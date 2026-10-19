import unittest
from app import app
from utils.job_discovery.location_prioritizer import get_location_rank, get_location_region_label
from utils.job_discovery.discovery_service import job_discovery_service
from models import JobListing


class TestJobRegionalPrioritization(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_location_rank_keywords(self):
        # India locations
        self.assertEqual(get_location_rank("Bengaluru, Karnataka (Hybrid)"), 0)
        self.assertEqual(get_location_rank("Pune, Maharashtra"), 0)
        self.assertEqual(get_location_rank("Mumbai"), 0)
        self.assertEqual(get_location_rank("Hyderabad, Telangana"), 0)
        self.assertEqual(get_location_rank("Chennai, Tamil Nadu"), 0)
        self.assertEqual(get_location_rank("Gurgaon, Delhi NCR"), 0)
        self.assertEqual(get_location_rank("Noida, Uttar Pradesh"), 0)
        self.assertEqual(get_location_rank("Tenkasi, Tamil Nadu"), 0)

        # Asia locations
        self.assertEqual(get_location_rank("Singapore (Hybrid)"), 1)
        self.assertEqual(get_location_rank("Tokyo, Japan"), 1)
        self.assertEqual(get_location_rank("Seoul, South Korea"), 1)
        self.assertEqual(get_location_rank("Dubai, UAE"), 1)
        self.assertEqual(get_location_rank("Kuala Lumpur, Malaysia"), 1)

        # Remote
        self.assertEqual(get_location_rank("Remote"), 2)
        self.assertEqual(get_location_rank("Work from home"), 2)

        # Other international
        self.assertEqual(get_location_rank("Düsseldorf, Germany"), 3)
        self.assertEqual(get_location_rank("Bad Salzungen, Deutschland"), 3)
        self.assertEqual(get_location_rank("San Francisco, CA, USA"), 3)

    def test_region_labels(self):
        self.assertEqual(get_location_region_label("Bengaluru"), "India")
        self.assertEqual(get_location_region_label("Singapore"), "Asia")
        self.assertEqual(get_location_region_label("Remote"), "Remote")
        self.assertEqual(get_location_region_label("Berlin, Germany"), "International")

    def test_job_search_strict_order(self):
        jobs = job_discovery_service.search_jobs(limit=100)
        self.assertGreater(len(jobs), 0)

        ranks = [j['location_rank'] for j in jobs]
        # Must be strictly ordered: rank 0 first, then rank 1, then rank 2, then rank 3
        self.assertEqual(ranks, sorted(ranks), "Jobs must be ordered by location rank (India -> Asia -> Remote -> Other)")

        # Verify first job is from India
        self.assertEqual(jobs[0]['location_rank'], 0)
        self.assertEqual(jobs[0]['region_badge'], "India")

    def test_job_search_region_filters(self):
        # Filter by India
        india_jobs = job_discovery_service.search_jobs(region='india', limit=50)
        for j in india_jobs:
            self.assertEqual(j['location_rank'], 0)
            self.assertEqual(j['region_badge'], 'India')

        # Filter by Asia
        asia_jobs = job_discovery_service.search_jobs(region='asia', limit=50)
        for j in asia_jobs:
            self.assertIn(j['location_rank'], [0, 1])

        # Filter by Remote
        remote_jobs = job_discovery_service.search_jobs(region='remote', limit=50)
        for j in remote_jobs:
            self.assertTrue(
                'remote' in j['work_arrangement'].lower() or j['location_rank'] == 2,
                f"Expected remote job, got {j['work_arrangement']} / rank {j['location_rank']}"
            )

    def test_job_listing_to_dict_metadata(self):
        job = JobListing.query.first()
        self.assertIsNotNone(job)
        d = job.to_dict()
        self.assertIn('region_badge', d)
        self.assertIn('location_rank', d)
        self.assertIn(d['region_badge'], ['India', 'Asia', 'Remote', 'International'])


if __name__ == '__main__':
    unittest.main()
