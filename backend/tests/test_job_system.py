"""
Tests for the job discovery system: providers, normalization, sync/dedup,
freshness & expiry, the two-hour scheduler & lease, search filters,
personalized matching, alerts and API authorization.

Run:  cd backend && python -m unittest discover -s tests -v
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import requests

from models import (JobListing, JobSyncRun, SchedulerLease, JobAlert, JobAlertMatch,
                    JobPreference, Skill, SkillVerification, AuditLog, Student)
from utils.job_discovery.base_adapter import (
    JobSourceAdapter, ProviderAuthError, ProviderRateLimited, ProviderTransientError,
    ProviderBadResponse, ProviderNotConfigured, RequestBudgetExceeded)
from utils.job_discovery.adzuna_adapter import AdzunaAdapter
from utils.job_discovery.jooble_adapter import JoobleAdapter, parse_jooble_salary
from utils.job_discovery.remote_api_adapter import _term_matches
from utils.job_discovery import normalizer as N
from utils.job_discovery import sync_service as S

UTC = timezone.utc
T0 = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
LONG_DESC = ("We are hiring. Requirements: strong Python and SQL skills, experience with Flask and Git. "
             "Nice to have: Docker and AWS. Work on real products with a friendly team.")


def raw_job(i=1, provider="fakeprov", **over):
    d = {"source_provider": provider, "source_name": "Fake Provider", "source_job_id": f"job-{i}",
         "title": f"Python Developer {i}", "company": f"Acme {i}", "description": LONG_DESC,
         "location": "Bengaluru, Karnataka", "url": f"https://jobs.example.com/view/{i}?utm_source=x",
         "posted_at": (T0 - timedelta(days=2)).isoformat(), "contract_type": "full_time permanent"}
    d.update(over)
    return d


class FakeAdapter(JobSourceAdapter):
    """In-memory provider. `jobs` may be a list, or an Exception to raise."""
    default_request_budget = 5

    def __init__(self, key="fakeprov", jobs=None, configured=True, **kw):
        self.provider_key = key
        super().__init__(**kw)
        self.jobs = jobs if jobs is not None else []
        self.configured = configured
        self.calls = 0

    @property
    def source_name(self):
        return f"Fake {self.provider_key}"

    def is_configured(self):
        return self.configured

    def fetch_jobs(self, searches):
        self.calls += 1
        if isinstance(self.jobs, Exception):
            raise self.jobs
        return [dict(j, source_provider=self.provider_key) for j in self.jobs] if self.calls == 1 else []


class FakeResponse:
    def __init__(self, status=200, payload=None, text="", bad_json=False):
        self.status_code = status
        self._payload = payload
        self.text = text
        self._bad = bad_json

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def sync(providers, now=T0, plan=None):
    return S.run_job_sync(trigger="cli", providers=providers,
                          search_plan=plan if plan is not None else [{"what": "python developer", "where": ""}],
                          now_fn=lambda: now)


# ════════════════════════════════════════════════════════════════════════
class ProviderTests(unittest.TestCase):
    def _adzuna(self, responses, **kw):
        a = AdzunaAdapter(app_id="id", app_key="key", session=FakeSession(responses), **kw)
        a._sleep = lambda s: a.__dict__.setdefault("slept", []).append(s)
        return a

    def test_adzuna_not_configured(self):
        with self.assertRaises(ProviderNotConfigured):
            AdzunaAdapter(app_id="", app_key="").fetch_jobs([{"what": "python"}])

    def test_adzuna_auth_failure_not_retried(self):
        a = self._adzuna([FakeResponse(401, text="bad key")])
        with self.assertRaises(ProviderAuthError):
            a.fetch_jobs([{"what": "python"}])
        self.assertEqual(a.requests_made, 1)

    def test_adzuna_rate_limited(self):
        a = self._adzuna([FakeResponse(429)])
        with self.assertRaises(ProviderRateLimited):
            a.fetch_jobs([{"what": "python"}])

    def test_timeout_retried_with_exponential_backoff(self):
        ok = FakeResponse(200, {"results": []})
        a = self._adzuna([requests.Timeout(), requests.ConnectionError(), ok], max_retries=3,
                         backoff_base_seconds=1.0)
        self.assertEqual(a.fetch_jobs([{"what": "python"}]), [])
        self.assertEqual(len(a.slept), 2)
        self.assertGreaterEqual(a.slept[1], 2 * 1.0)   # 1s, then 2s (+jitter)

    def test_server_errors_exhaust_retries(self):
        a = self._adzuna([FakeResponse(503)] * 4, max_retries=3)
        with self.assertRaises(ProviderTransientError):
            a.fetch_jobs([{"what": "python"}])

    def test_bad_json(self):
        a = self._adzuna([FakeResponse(200, bad_json=True)])
        with self.assertRaises(ProviderBadResponse):
            a.fetch_jobs([{"what": "python"}])

    def test_empty_results(self):
        a = self._adzuna([FakeResponse(200, {"results": []})])
        self.assertEqual(a.fetch_jobs([{"what": "python"}]), [])

    def test_request_budget_stops_paging(self):
        a = self._adzuna([FakeResponse(200, {"results": []})] * 5, max_requests_per_run=2)
        a.fetch_jobs([{"what": "a"}, {"what": "b"}, {"what": "c"}])
        self.assertEqual(a.requests_made, 2)

    def test_adzuna_field_mapping_and_estimated_salary(self):
        payload = {"results": [{
            "id": "123", "title": "Data Analyst", "description": "snippet", "created": "2026-11-10T09:00:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/123", "company": {"display_name": "Acme"},
            "location": {"display_name": "Bengaluru, Karnataka", "area": ["India", "Karnataka", "Bengaluru"]},
            "salary_min": 500000, "salary_max": 700000, "salary_is_predicted": "1",
            "contract_time": "full_time"}]}
        a = self._adzuna([FakeResponse(200, payload)])
        job = a.fetch_jobs([{"what": "data analyst", "where": "Bengaluru"}])[0]
        self.assertEqual(job["source_job_id"], "123")
        self.assertEqual(job["salary_currency"], "INR")
        self.assertTrue(job["salary_is_estimated"])
        self.assertEqual(job["country"], "India")
        method, url, kw = a.session.calls[0]
        self.assertIn("/jobs/in/search/1", url)
        self.assertEqual(kw["params"]["where"], "Bengaluru")

    def test_api_key_never_in_error_message(self):
        a = JoobleAdapter(api_key="SECRET123", session=FakeSession([requests.ConnectionError("x")] * 5),
                          max_retries=1)
        a._sleep = lambda s: None
        with self.assertRaises(ProviderTransientError) as ctx:
            a.fetch_jobs([{"what": "python"}])
        self.assertNotIn("SECRET123", str(ctx.exception))

    def test_jooble_request_and_no_posting_date(self):
        payload = {"totalCount": 1, "jobs": [{"id": 9, "title": "Java Developer", "location": "Mangaluru",
                                               "snippet": "Java role", "salary": "₹30,000 - ₹45,000 per month",
                                               "source": "naukri.com", "type": "Full-time",
                                               "link": "https://in.jooble.org/desc/9", "company": "Acme",
                                               "updated": "2026-11-11T00:00:00.0000000"}]}
        a = JoobleAdapter(api_key="k", session=FakeSession([FakeResponse(200, payload)]))
        job = a.fetch_jobs([{"what": "java developer", "where": "Mangaluru"}])[0]
        method, url, kw = a.session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://in.jooble.org/api/k")
        self.assertEqual(kw["json"]["keywords"], "java developer")
        self.assertIsNone(job["posted_at"])            # 'updated' is not a posting date
        self.assertEqual((job["salary_min"], job["salary_max"], job["salary_period"]), (30000, 45000, "month"))

    def test_jooble_salary_parsing(self):
        self.assertEqual(parse_jooble_salary("6 - 9 lakh per year"), (600000.0, 900000.0, "INR", "year"))
        self.assertEqual(parse_jooble_salary("Competitive"), (None, None, None, None))
        self.assertEqual(parse_jooble_salary("$20 per hour")[2:], ("USD", "hour"))

    def test_arbeitnow_term_matching(self):
        self.assertFalse(_term_matches("ai engineer remote", "Projektmanager TGA - Remote (DE)"))
        self.assertTrue(_term_matches("python developer", "Senior Python Developer"))
        self.assertFalse(_term_matches("java developer", "JavaScript Developer"))
        self.assertTrue(_term_matches("ai engineer", "AI Engineer (m/w/d)"))


# ════════════════════════════════════════════════════════════════════════
GH_PAYLOAD = {"jobs": [
    {"id": 101, "title": "Software Engineer - Backend", "company_name": "Acme",
     "absolute_url": "https://boards.greenhouse.io/acme/jobs/101", "location": {"name": "Bengaluru, India"},
     "first_published": "2026-11-10T09:00:00-04:00", "updated_at": "2026-11-12T09:00:00-04:00",
     "content": "&lt;p&gt;Requirements: Python, SQL and Docker. Nice to have: AWS.&lt;/p&gt;" + "&lt;p&gt;x&lt;/p&gt;" * 10,
     "metadata": [{"name": "Employment Type", "value": "Full-time"}]},
    {"id": 102, "title": "Software Engineer", "company_name": "Acme",
     "absolute_url": "https://boards.greenhouse.io/acme/jobs/102", "location": {"name": "San Francisco, CA"},
     "content": "US only role " * 10},
    {"id": 103, "title": "Senior Accountant", "company_name": "Acme",
     "absolute_url": "https://boards.greenhouse.io/acme/jobs/103", "location": {"name": "Mumbai, India"},
     "content": "Finance role " * 10},
]}
LEVER_PAYLOAD = [
    {"id": "aaa-1", "text": "Data Analyst Intern", "hostedUrl": "https://jobs.lever.co/beta/aaa-1",
     "categories": {"location": "hyderabad", "commitment": "intern"}, "country": "IN", "workplaceType": "hybrid",
     "createdAt": 1762934400000, "descriptionPlain": "Analyse business data for product teams.",
     "lists": [{"text": "Requirements", "content": "<li>SQL</li><li>Excel and Power BI</li>"}]},
    {"id": "aaa-2", "text": "Backend Developer", "hostedUrl": "https://jobs.lever.co/beta/aaa-2",
     "categories": {"location": "Remote - US"}, "country": "US", "workplaceType": "remote",
     "descriptionPlain": "US remote " * 10},
]


class CompanyBoardTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def _gh(self, responses, boards=("acme",)):
        from utils.job_discovery.company_boards_adapter import GreenhouseBoardsAdapter
        a = GreenhouseBoardsAdapter(boards=list(boards), session=FakeSession(responses))
        a._sleep = lambda s: None
        return a

    def test_greenhouse_mapping_and_filters(self):
        a = self._gh([FakeResponse(200, GH_PAYLOAD)])
        a.reset_run_state()
        jobs = a.fetch_jobs()
        self.assertEqual([j["source_job_id"] for j in jobs], ["acme:101"])   # US + accountant filtered out
        self.assertEqual(a.filtered_out, 2)
        j = jobs[0]
        self.assertEqual(j["posted_at"], "2026-11-10T09:00:00-04:00")       # first_published, not updated_at
        self.assertEqual(j["contract_type"], "Full-time")
        self.assertEqual(a.completed_scopes["greenhouse:acme:"],
                         {"greenhouse:acme:101", "greenhouse:acme:102", "greenhouse:acme:103"})
        norm, _ = N.normalize_job(j)
        self.assertEqual(set(norm["required_skills"]), {"python", "sql", "docker"})
        self.assertEqual(norm["preferred_skills"], ["aws"])

    def test_lever_mapping_and_filters(self):
        from utils.job_discovery.company_boards_adapter import LeverBoardsAdapter
        a = LeverBoardsAdapter(boards=["beta"], session=FakeSession([FakeResponse(200, LEVER_PAYLOAD)]))
        a.reset_run_state()
        jobs = a.fetch_jobs()
        self.assertEqual(len(jobs), 1)                                        # US-remote role skipped
        norm, reason = N.normalize_job(jobs[0])
        self.assertIsNone(reason)
        self.assertEqual(norm["job_type"], "Internship")
        self.assertEqual(norm["work_arrangement"], "Hybrid")
        self.assertEqual(norm["country"], "India")
        self.assertIsNotNone(norm["posting_date"])
        self.assertTrue({"sql", "excel", "power bi"} <= set(norm["required_skills"]))

    def test_one_board_failing_does_not_stop_others(self):
        a = self._gh([FakeResponse(404, text="no such board"), FakeResponse(200, GH_PAYLOAD)], boards=("gone", "acme"))
        a.reset_run_state()
        jobs = a.fetch_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertTrue(a.run_errors and a.run_errors[0].startswith("gone:"))
        self.assertNotIn("greenhouse:gone:", a.completed_scopes)

    def test_removed_posting_expired_as_confirmed(self):
        sync([self._gh([FakeResponse(200, GH_PAYLOAD)])])
        job = JobListing.query.filter_by(external_id="greenhouse:acme:101").first()
        self.assertEqual(job.status, "active")
        emptied = {"jobs": [GH_PAYLOAD["jobs"][1]]}                          # 101 removed by the employer
        run = sync([self._gh([FakeResponse(200, emptied)])], now=T0 + timedelta(hours=2))
        job = JobListing.query.filter_by(external_id="greenhouse:acme:101").first()
        self.assertEqual(job.status, "expired")
        self.assertIn("confirmed by the source", job.expiry_reason)
        self.assertEqual(run["provider_results"]["greenhouse"]["confirmed_removed"], 1)

    def test_title_filter_excludes_finance_keeps_tech(self):
        from utils.job_discovery.company_boards_adapter import is_relevant_title
        self.assertFalse(is_relevant_title("AP & Expenses Projects Analyst"))
        self.assertFalse(is_relevant_title("Senior Accountant"))
        self.assertTrue(is_relevant_title("AR/VR Engineer"))
        self.assertTrue(is_relevant_title("Data Analyst Intern"))

    def test_city_aliases(self):
        self.assertEqual(N.split_location("Bangalore, IND")["city"], "Bengaluru")
        self.assertEqual(N.split_location("Bangalore, IND")["country"], "India")
        self.assertEqual(N.split_location("Hybrid in Bangalore")["city"], "Bengaluru")
        self.assertIn("bangalore", N.location_search_terms("Bengaluru"))
        sync([FakeAdapter(jobs=[raw_job(1, location="Bangalore, India"), raw_job(2, location="Gurgaon, India")])],
             now=datetime.now(UTC))
        from utils.job_discovery import job_discovery_service
        self.assertEqual(len(job_discovery_service.search_jobs(location="Bengaluru")), 1)
        self.assertEqual(len(job_discovery_service.search_jobs(location="Gurugram")), 1)

    def test_failed_board_does_not_expire_its_jobs(self):
        sync([self._gh([FakeResponse(200, GH_PAYLOAD)])])
        sync([self._gh([FakeResponse(503)] * 3)], now=T0 + timedelta(hours=2))
        self.assertEqual(JobListing.query.filter_by(external_id="greenhouse:acme:101").first().status, "active")


# ════════════════════════════════════════════════════════════════════════
class NormalizerTests(unittest.TestCase):
    def test_rejects_missing_url_title_company(self):
        self.assertEqual(N.normalize_job(raw_job(url=""))[1], "missing or invalid job URL")
        self.assertEqual(N.normalize_job(raw_job(title=""))[1], "missing title")
        self.assertEqual(N.normalize_job(raw_job(company=None))[1], "missing company")
        self.assertEqual(N.normalize_job(raw_job(description="short"))[1], "description too short to evaluate")

    def test_no_invented_values(self):
        norm, _ = N.normalize_job(raw_job(description="A role in our team building things for customers every day.",
                                          posted_at=None))
        self.assertEqual(norm["required_skills"], [])          # no ["python","git"] fallback
        self.assertEqual(norm["skills_source"], "none")
        self.assertIsNone(norm["posting_date"])                 # not "now"
        self.assertIsNone(norm["salary_min"])

    def test_future_posting_date_dropped(self):
        norm, _ = N.normalize_job(raw_job(posted_at=(datetime.now(UTC) + timedelta(days=5)).isoformat()))
        self.assertIsNone(norm["posting_date"])

    def test_required_vs_preferred(self):
        norm, _ = N.normalize_job(raw_job())
        self.assertEqual(set(norm["required_skills"]), {"python", "sql", "flask", "git"})
        self.assertEqual(set(norm["preferred_skills"]), {"docker", "aws"})

    def test_bulleted_sections(self):
        desc = ("About the role: build data products.\nRequirements:\n• Python\n• SQL and Tableau\n"
                "Nice to have:\n• Docker\n• Experience with AWS\n• Kubernetes is required for on-call")
        req, pref, src = N.split_required_preferred(desc)
        self.assertEqual(set(req), {"python", "sql", "tableau", "kubernetes"})
        self.assertEqual(set(pref), {"docker", "aws"})
        self.assertEqual(src, "description_text")

    def test_canonical_url_and_fingerprint(self):
        self.assertEqual(N.canonicalize_url("HTTPS://WWW.Example.com/jobs/1/?utm_source=a&b=2#top"),
                         "https://example.com/jobs/1?b=2")
        self.assertEqual(N.make_fingerprint("Python Developer", "Acme Pvt Ltd", "Bengaluru"),
                         N.make_fingerprint("python developer", "ACME", "bengaluru"))

    def test_experience_and_type_inference(self):
        e = N.infer_experience("Backend Developer", "We need 3-5 years of experience with Java.")
        self.assertEqual((e["experience_min_years"], e["experience_max_years"], e["experience_level"]),
                         (3.0, 5.0, "Mid-Level"))
        e = N.infer_experience("Graduate Engineer Trainee", "Freshers welcome.")
        self.assertTrue(e["is_entry_level"])
        self.assertEqual(N.infer_job_type("Data Science Intern", None, ""), "Internship")
        self.assertEqual(N.infer_work_arrangement("Dev", "Bengaluru (Hybrid)", "", None), "Hybrid")


# ════════════════════════════════════════════════════════════════════════
class SyncTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_insert_then_rerun_is_idempotent(self):
        run = sync([FakeAdapter(jobs=[raw_job(1), raw_job(2)])])
        self.assertEqual((run["status"], run["inserted_count"]), ("success", 2))
        run2 = sync([FakeAdapter(jobs=[raw_job(1), raw_job(2)])], now=T0 + timedelta(hours=2))
        self.assertEqual((run2["inserted_count"], run2["unchanged_count"]), (0, 2))
        self.assertEqual(JobListing.query.count(), 2)
        job = JobListing.query.filter_by(source_job_id="job-1").first()
        self.assertEqual(job.times_seen, 2)
        self.assertEqual(job.last_verified_at, (T0 + timedelta(hours=2)).replace(tzinfo=None))
        # re-fetching must NOT make an old job look newly posted
        self.assertEqual(job.posting_date, (T0 - timedelta(days=2)).replace(tzinfo=None))

    def test_changed_listing_is_updated(self):
        sync([FakeAdapter(jobs=[raw_job(1)])])
        changed = raw_job(1, description=LONG_DESC + " Kubernetes is required.", title="Python Developer 1 (Updated)")
        run = sync([FakeAdapter(jobs=[changed])], now=T0 + timedelta(hours=2))
        self.assertEqual(run["updated_count"], 1)
        job = JobListing.query.filter_by(source_job_id="job-1").first()
        self.assertEqual(job.title, "Python Developer 1 (Updated)")
        self.assertIn("kubernetes", job.get_required_skills())
        self.assertIsNotNone(job.last_changed_at)

    def test_cross_provider_duplicate_flagged_not_merged(self):
        sync([FakeAdapter("prov_a", jobs=[raw_job(1)]),
              FakeAdapter("prov_b", jobs=[raw_job(1, source_job_id="other-77", url="https://other.example/77")])])
        rows = JobListing.query.order_by(JobListing.id).all()
        self.assertEqual(len(rows), 2)                       # both stored with attribution
        self.assertIsNone(rows[0].duplicate_of_id)
        self.assertEqual(rows[1].duplicate_of_id, rows[0].id)
        from utils.job_discovery import job_discovery_service
        visible = job_discovery_service.search_jobs(limit=50)
        self.assertEqual(len(visible), 1)                    # duplicate hidden from search

    def test_same_provider_same_title_different_ids_are_distinct(self):
        run = sync([FakeAdapter(jobs=[raw_job(1), raw_job(1, source_job_id="job-1b", url="https://jobs.example.com/view/1b")])])
        self.assertEqual(run["duplicate_count"], 0)
        self.assertEqual(JobListing.query.filter(JobListing.duplicate_of_id.isnot(None)).count(), 0)

    def test_expiry_rules(self):
        sync([FakeAdapter(jobs=[raw_job(1), raw_job(2, deadline=(T0 + timedelta(days=1)).isoformat()), raw_job(3)])])
        # 4 days later the provider is healthy but stopped returning job 3 -> stale; deadline of job 2 passed
        later = T0 + timedelta(days=4)
        sync([FakeAdapter(jobs=[raw_job(1), raw_job(2, deadline=(T0 + timedelta(days=1)).isoformat())])], now=later)
        j1, j2, j3 = (JobListing.query.filter_by(source_job_id=f"job-{i}").first() for i in (1, 2, 3))
        self.assertEqual(j1.status, "active")
        self.assertEqual(j2.status, "expired")
        self.assertIn("deadline", j2.expiry_reason.lower())
        self.assertEqual(j3.status, "stale")
        # 22 days unseen -> archived with an honest reason
        sync([FakeAdapter(jobs=[raw_job(1)])], now=T0 + timedelta(days=22))
        j3 = JobListing.query.filter_by(source_job_id="job-3").first()
        self.assertEqual(j3.status, "expired")
        self.assertIn("not confirmed by the source", j3.expiry_reason)

    def test_provider_outage_never_expires_listings(self):
        sync([FakeAdapter(jobs=[raw_job(1)])])
        run = sync([FakeAdapter(jobs=ProviderTransientError("down"))], now=T0 + timedelta(days=30))
        self.assertEqual(run["status"], "failed")
        self.assertEqual(JobListing.query.filter_by(source_job_id="job-1").first().status, "active")

    def test_old_posting_still_listed_stays_active(self):
        # employer still lists a 90-day-old posting -> the source confirms it is open
        sync([FakeAdapter(jobs=[raw_job(1, posted_at=(T0 - timedelta(days=90)).isoformat())])])
        self.assertEqual(JobListing.query.first().status, "active")

    def test_old_posting_not_reconfirmed_expires(self):
        sync([FakeAdapter(jobs=[raw_job(1, posted_at=(T0 - timedelta(days=58)).isoformat())])])
        # 5 days later: provider healthy, job not returned again, now 63 days old
        sync([FakeAdapter(jobs=[raw_job(2)])], now=T0 + timedelta(days=5))
        job = JobListing.query.filter_by(source_job_id="job-1").first()
        self.assertEqual(job.status, "expired")
        self.assertIn("not re-confirmed", job.expiry_reason)

    def test_reappearing_job_is_reactivated(self):
        sync([FakeAdapter(jobs=[raw_job(1)])])
        sync([FakeAdapter(jobs=[raw_job(2)])], now=T0 + timedelta(days=4))
        self.assertEqual(JobListing.query.filter_by(source_job_id="job-1").first().status, "stale")
        sync([FakeAdapter(jobs=[raw_job(1)])], now=T0 + timedelta(days=5))
        self.assertEqual(JobListing.query.filter_by(source_job_id="job-1").first().status, "active")

    def test_invalid_jobs_counted_with_reasons(self):
        run = sync([FakeAdapter(jobs=[raw_job(1), raw_job(2, url="not-a-url")])])
        self.assertEqual(run["invalid_count"], 1)
        self.assertEqual(run["provider_results"]["fakeprov"]["rejection_reasons"], {"missing or invalid job URL": 1})

    def test_auth_and_rate_limit_recorded_per_provider(self):
        run = sync([FakeAdapter("a", jobs=ProviderAuthError("bad key")),
                    FakeAdapter("b", jobs=ProviderRateLimited("429")),
                    FakeAdapter("c", jobs=[raw_job(1)])])
        pr = run["provider_results"]
        self.assertEqual((pr["a"]["status"], pr["b"]["status"], pr["c"]["status"]),
                         ("auth_failed", "rate_limited", "ok"))
        self.assertEqual(run["status"], "partial")

    def test_no_configured_provider_fails_honestly(self):
        run = sync([FakeAdapter(configured=False)])
        self.assertEqual(run["status"], "failed")
        self.assertIn("No job provider is configured", run["error"])

    def test_sample_listings_never_mixed_into_default_search(self):
        sync([FakeAdapter("curated_sample", jobs=[raw_job(1, is_sample=True)]), FakeAdapter(jobs=[raw_job(2)])])
        from utils.job_discovery import job_discovery_service
        titles = [j["title"] for j in job_discovery_service.search_jobs()]
        self.assertEqual(titles, ["Python Developer 2"])
        self.assertEqual(len(job_discovery_service.search_jobs(is_sample=True)), 1)


# ════════════════════════════════════════════════════════════════════════
class SchedulerAndLeaseTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def _at(self, now):
        return mock.patch.object(S, "_now", lambda: now)

    def test_due_when_never_run(self):
        self.assertTrue(S.is_due())

    def test_two_hour_interval(self):
        sync([FakeAdapter(jobs=[raw_job(1)])], now=T0)
        with self._at(T0 + timedelta(hours=1, minutes=59)):
            self.assertFalse(S.is_due())
        with self._at(T0 + timedelta(hours=2)):
            self.assertTrue(S.is_due())

    def test_failed_run_retried_sooner(self):
        sync([FakeAdapter(jobs=ProviderTransientError("down"))], now=T0)
        with self._at(T0 + timedelta(minutes=10)):
            self.assertFalse(S.is_due())
        with self._at(T0 + timedelta(minutes=21)):
            self.assertTrue(S.is_due())

    def test_restart_recovery_uses_database_state(self):
        sync([FakeAdapter(jobs=[raw_job(1)])], now=T0)
        db.session.remove()  # simulate a new process: nothing kept in memory
        with self._at(T0 + timedelta(hours=3)):
            self.assertTrue(S.is_due())
        # a run that crashed mid-way (left 'running') is retried after the lease TTL
        db.session.add(JobSyncRun(trigger="scheduled", status="running",
                                  started_at=(T0 + timedelta(hours=3)).replace(tzinfo=None)))
        db.session.commit()
        with self._at(T0 + timedelta(hours=3, minutes=10)):
            self.assertFalse(S.is_due())
        with self._at(T0 + timedelta(hours=3, minutes=31)):
            self.assertTrue(S.is_due())

    def test_overlapping_runs_are_prevented(self):
        self.assertTrue(S.acquire_lease("worker-1"))
        self.assertFalse(S.acquire_lease("worker-2"))
        run = sync([FakeAdapter(jobs=[raw_job(1)])])
        self.assertEqual(run["status"], "skipped")
        self.assertEqual(JobListing.query.count(), 0)
        S.release_lease("worker-1")
        self.assertTrue(S.acquire_lease("worker-2"))
        S.release_lease("worker-2")

    def test_expired_lease_can_be_taken_over(self):
        self.assertTrue(S.acquire_lease("crashed-worker", ttl=timedelta(seconds=-1)))
        self.assertTrue(S.acquire_lease("new-worker"))
        S.release_lease("new-worker")

    def test_lease_released_even_after_crash(self):
        with mock.patch.object(S, "apply_expiry", side_effect=RuntimeError("boom")):
            run = sync([FakeAdapter(jobs=[raw_job(1)])])
        self.assertEqual(run["status"], "failed")
        self.assertIn("boom", run["error"])
        self.assertFalse(S.lease_status()["running"])

    def test_scheduler_run_if_due(self):
        from utils.job_discovery.scheduler import run_if_due
        with mock.patch.object(S, "build_providers", lambda: [FakeAdapter(jobs=[raw_job(1)])]):
            first = run_if_due(app)
            second = run_if_due(app)
        self.assertEqual(first["status"], "success")
        self.assertIsNone(second)   # not due again within two hours

    def test_search_plan_rotates_and_includes_user_demand(self):
        make_student("plan@x.edu", target_career="Blockchain Developer")
        plan = S.build_search_plan()
        self.assertEqual(plan[0]["what"], "blockchain developer")
        s1 = S.plan_slice(plan, 5, 0)
        s2 = S.plan_slice(plan, 5, 5)
        self.assertNotEqual(s1, s2)


# ════════════════════════════════════════════════════════════════════════
class SearchAndMatchingTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()
        jobs = [
            raw_job(1, title="Software Engineer Intern", description="Internship. " + LONG_DESC,
                    posted_at=(T0 - timedelta(days=1)).isoformat()),
            raw_job(2, title="Senior Java Developer", location="Pune, Maharashtra",
                    description="We need 6+ years of experience. Requirements: Java, Spring Boot, SQL and Kubernetes. "
                                "You will lead a team.", posted_at=(T0 - timedelta(days=10)).isoformat(),
                    salary_min=2000000, salary_max=3000000, salary_currency="INR", salary_period="year"),
            raw_job(3, title="Data Analyst", company="Beta Analytics", location="Mangaluru, Karnataka",
                    description="Requirements: SQL, Excel and Power BI dashboards for business teams. Freshers welcome.",
                    posted_at=None),
        ]
        sync([FakeAdapter(jobs=jobs)], now=datetime.now(UTC))
        from utils.job_discovery import job_discovery_service
        self.svc = job_discovery_service

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def titles(self, **kw):
        return [j["title"] for j in self.svc.search_jobs(**kw)]

    def test_filters(self):
        self.assertEqual(self.titles(internship=True), ["Software Engineer Intern"])
        self.assertNotIn("Senior Java Developer", self.titles(entry_level=True))
        self.assertEqual(self.titles(location="Mangaluru"), ["Data Analyst"])
        self.assertEqual(self.titles(company="beta"), ["Data Analyst"])
        self.assertEqual(self.titles(skill="power bi"), ["Data Analyst"])
        self.assertEqual(self.titles(salary_min=1500000), ["Senior Java Developer"])
        self.assertNotIn("Senior Java Developer", self.titles(experience_max=2))
        self.assertEqual(self.titles(date_posted="3d"), ["Software Engineer Intern"])

    def test_sorting_and_pagination(self):
        recent = self.titles(sort="recent")
        self.assertEqual(recent[-1], "Data Analyst")              # unknown posting date sorts last
        self.assertEqual(self.titles(sort="salary")[0], "Senior Java Developer")
        page = self.svc.search_jobs(limit=2, page=2, return_meta=True)
        self.assertEqual((page["total"], page["pages"], len(page["jobs"])), (3, 2, 1))

    def test_freshness_labels(self):
        job = next(j for j in self.svc.search_jobs() if j["title"] == "Data Analyst")
        self.assertEqual(job["freshness"]["posted_label"], "Posting date not provided")
        self.assertEqual(job["freshness"]["verification_status"], "verified")

    def test_match_weights_mandatory_over_preferred_and_ignores_title(self):
        from utils.job_matcher import evaluate_job_match
        job = {"title": "Python Developer", "required_skills": ["python", "sql", "flask"],
               "preferred_skills": ["docker", "aws"]}
        has_required = evaluate_job_match(user_skills=[{"skill_name": s, "is_verified": True}
                                                       for s in ("python", "sql", "flask")], job_data=job)
        has_preferred = evaluate_job_match(user_skills=[{"skill_name": s, "is_verified": True}
                                                        for s in ("docker", "aws", "python")], job_data=job)
        self.assertGreater(has_required["match_score"], has_preferred["match_score"])
        nothing = evaluate_job_match(user_skills=[], job_data=job)
        self.assertEqual(nothing["match_score"], 0.0)           # title match gives no free points

    def test_verified_beats_resume_only_and_no_skills_is_none(self):
        from utils.job_matcher import evaluate_job_match
        job = {"required_skills": ["python", "sql"], "preferred_skills": []}
        v = evaluate_job_match(user_skills=[{"skill_name": "python", "is_verified": True},
                                            {"skill_name": "sql", "is_verified": True}], job_data=job)
        r = evaluate_job_match(user_skills=[{"skill_name": "python", "evidence_strength": "listed_only"},
                                            {"skill_name": "sql", "evidence_strength": "listed_only"}], job_data=job)
        self.assertEqual(v["match_score"], 100.0)
        self.assertLess(r["match_score"], v["match_score"])
        none = evaluate_job_match(user_skills=["python"], job_data={"required_skills": [], "preferred_skills": []})
        self.assertIsNone(none["match_score"])

    def test_experience_and_location_affect_score(self):
        from utils.job_matcher import evaluate_job_match, build_student_profile
        sid = make_student("m@x.edu")
        student = db.session.get(Student, sid)
        s = Skill(student_id=sid, skill_name="java", extraction_confidence=1.0, evidence_strength="applied")
        db.session.add(s)
        db.session.add(JobPreference(student_id=sid, preferred_locations=json.dumps(["Bengaluru"]),
                                     work_modes=json.dumps([]), experience_years=0))
        db.session.commit()
        job = JobListing.query.filter_by(title="Senior Java Developer").first()
        ev = evaluate_job_match(student=student, job=job, include_resources=False)
        self.assertFalse(ev["eligibility_status"]["meets_criteria"])
        self.assertFalse(ev["location_compatibility"]["compatible"])
        self.assertIn("Missing required skills", " ".join(ev["match_reasons"]))
        self.assertLess(ev["scoring_breakdown"]["experience_eligibility_score"], 100)


# ════════════════════════════════════════════════════════════════════════
class AlertTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()
        self.sid = make_student("alerts@x.edu")
        for name in ("python", "sql", "flask", "git"):
            sk = Skill(student_id=self.sid, skill_name=name, extraction_confidence=1.0, evidence_strength="applied")
            db.session.add(sk)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def _alert(self, freq="instant", **kw):
        a = JobAlert(student_id=self.sid, name="py", roles=json.dumps(["python developer"]),
                     locations=json.dumps(kw.get("locations", [])), skills="[]", job_types="[]", work_modes="[]",
                     min_match_score=kw.get("min_match", 30), frequency=freq, is_active=True)
        db.session.add(a)
        db.session.commit()
        return a

    def test_instant_alert_created_once(self):
        self._alert("instant")
        r1 = sync([FakeAdapter(jobs=[raw_job(1)])])
        self.assertEqual(r1["alerts_created"], 1)
        m = JobAlertMatch.query.first()
        self.assertIsNotNone(m.released_at)
        r2 = sync([FakeAdapter(jobs=[raw_job(1)])], now=T0 + timedelta(hours=2))
        self.assertEqual(r2["alerts_created"], 0)                 # existing job, not re-alerted
        self.assertEqual(JobAlertMatch.query.count(), 1)

    def test_daily_alert_held_then_released(self):
        from utils.job_alerts import release_due_alert_matches
        a = self._alert("daily")
        a.last_notified_at = T0.replace(tzinfo=None)
        db.session.commit()
        sync([FakeAdapter(jobs=[raw_job(1)])], now=T0 + timedelta(hours=1))
        self.assertIsNone(JobAlertMatch.query.first().released_at)
        release_due_alert_matches(T0 + timedelta(hours=25))
        self.assertIsNotNone(JobAlertMatch.query.first().released_at)

    def test_alert_filters_and_threshold(self):
        self._alert("instant", locations=["Pune"])
        sync([FakeAdapter(jobs=[raw_job(1)])])                      # Bengaluru job
        self.assertEqual(JobAlertMatch.query.count(), 0)

    def test_alert_volume_cap(self):
        from utils import job_alerts
        self._alert("instant")
        with mock.patch.object(job_alerts, "MAX_MATCHES_PER_ALERT_PER_RUN", 3):
            sync([FakeAdapter(jobs=[raw_job(i) for i in range(1, 8)])])
        self.assertEqual(JobAlertMatch.query.count(), 3)


# ════════════════════════════════════════════════════════════════════════
class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.student_id = make_student("student@x.edu")
        self.other_id = make_student("other@x.edu")
        self.admin_id = make_student("admin@x.edu", role="admin")
        self.client = app.test_client()

    def test_register_cannot_self_assign_admin(self):
        res = self.client.post("/api/auth/register", json={
            "name": "Mallory", "email": "mallory@x.edu", "password": "password123",
            "college": "c", "course": "c", "role": "admin"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["student"]["role"], "student")
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 403)

    def test_student_cannot_trigger_sync(self):
        login(self.client, "student@x.edu")
        res = self.client.post("/api/student/jobs/sync")
        self.assertEqual(res.status_code, 403)
        self.assertIn("next_scheduled_sync", res.get_json())
        self.assertEqual(self.client.post("/api/admin/jobs/sync").status_code, 403)

    def test_admin_manual_sync_audited_and_overview(self):
        login(self.client, "admin@x.edu")
        with mock.patch.object(S, "build_providers", lambda: [FakeAdapter(jobs=[raw_job(1)])]):
            res = self.client.post("/api/admin/jobs/sync")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["run"]["inserted_count"], 1)
        with app.app_context():
            self.assertEqual(AuditLog.query.filter_by(action="jobs.manual_sync").count(), 1)
        ov = self.client.get("/api/admin/jobs/overview").get_json()
        self.assertEqual(ov["totals"]["jobs_total"], 1)
        self.assertIn("next_scheduled_sync", ov["schedule"])

    def test_manual_sync_during_scheduled_run_is_rejected(self):
        login(self.client, "admin@x.edu")
        with app.app_context():
            S.acquire_lease("scheduler")
        res = self.client.post("/api/admin/jobs/sync")
        self.assertEqual(res.status_code, 409)
        with app.app_context():
            S.release_lease("scheduler")

    def test_alert_crud_validation_and_isolation(self):
        login(self.client, "student@x.edu")
        self.assertEqual(self.client.post("/api/student/job_alerts", json={"name": "x"}).status_code, 400)
        self.assertEqual(self.client.post("/api/student/job_alerts",
                                          json={"name": "x", "roles": ["dev"], "frequency": "hourly"}).status_code, 400)
        res = self.client.post("/api/student/job_alerts", json={"name": "Py", "roles": ["python developer"],
                                                                "frequency": "daily", "min_match_score": 40})
        self.assertEqual(res.status_code, 201)
        alert_id = res.get_json()["alert"]["id"]
        other = app.test_client()
        login(other, "other@x.edu")
        self.assertEqual(other.put(f"/api/student/job_alerts/{alert_id}", json={"name": "hijack"}).status_code, 404)
        self.assertEqual(other.delete(f"/api/student/job_alerts/{alert_id}").status_code, 404)
        self.assertEqual(other.get("/api/student/job_alerts").get_json()["alerts"], [])

    def test_preferences_validation(self):
        login(self.client, "student@x.edu")
        self.assertEqual(self.client.put("/api/student/job_preferences", json={"experience_years": -3}).status_code, 400)
        res = self.client.put("/api/student/job_preferences",
                              json={"preferred_locations": ["Bengaluru"], "work_modes": ["Remote", "bogus"],
                                    "experience_years": 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["preferences"]["work_modes"], ["Remote"])

    def test_jobs_endpoint_returns_pagination_and_match(self):
        with app.app_context():
            sync([FakeAdapter(jobs=[raw_job(i) for i in range(1, 4)])], now=datetime.now(UTC))
        login(self.client, "student@x.edu")
        data = self.client.get("/api/student/jobs?per_page=2&page=1&sort=recent").get_json()
        self.assertEqual((data["total"], data["pages"], len(data["jobs"])), (3, 2, 2))
        self.assertIn("match_score", data["jobs"][0])
        self.assertIn("freshness", data["jobs"][0])


if __name__ == "__main__":
    unittest.main()
