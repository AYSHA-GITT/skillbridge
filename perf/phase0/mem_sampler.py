"""
Samples a container's cgroup v2 memory from the HOST every 0.25 s (so sampling
adds nothing to the container's own memory) and records the peak per test phase.

  memory.current : everything the kernel charges to the container (RSS + page cache + kernel)
  anon           : process memory that cannot be reclaimed (the part that causes OOM kills)
  memory.peak    : kernel-tracked high-water mark of memory.current
  memory.events  : oom / oom_kill counters (any oom_kill > 0 means FAIL)

The current phase name is read from <phase_file>, written by the driver.
Usage: python mem_sampler.py <container_id> <phase_file> <stop_file> <out_json>
"""
import glob
import json
import os
import sys
import time


def cgroup_dir(cid):
    for pattern in (f"/sys/fs/cgroup/system.slice/docker-{cid}*.scope",
                    f"/sys/fs/cgroup/docker/{cid}*",
                    f"/sys/fs/cgroup/**/*{cid}*"):
        hits = [h for h in glob.glob(pattern, recursive=True) if os.path.isfile(os.path.join(h, "memory.current"))]
        if hits:
            return hits[0]
    raise SystemExit(f"cgroup for container {cid} not found")


def read(path, default=None):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def kv(path):
    out = {}
    for line in (read(path, "") or "").splitlines():
        k, _, v = line.partition(" ")
        if v.strip().isdigit():
            out[k] = int(v)
    return out


def main():
    cid, phase_file, stop_file, out_path = sys.argv[1:5]
    d = cgroup_dir(cid)
    mb = 1024 * 1024
    phases, timeline, t0 = {}, [], time.time()
    while not os.path.exists(stop_file):
        phase = read(phase_file, "startup") or "startup"
        cur = int(read(os.path.join(d, "memory.current"), "0") or 0)
        st = kv(os.path.join(d, "memory.stat"))
        anon = st.get("anon", 0)
        p = phases.setdefault(phase, {"max_current_mb": 0.0, "max_anon_mb": 0.0, "samples": 0})
        p["max_current_mb"] = max(p["max_current_mb"], round(cur / mb, 1))
        p["max_anon_mb"] = max(p["max_anon_mb"], round(anon / mb, 1))
        p["samples"] += 1
        if len(timeline) == 0 or time.time() - timeline[-1][0] - t0 >= 2:
            timeline.append([round(time.time() - t0, 1), phase, round(cur / mb, 1), round(anon / mb, 1)])
        time.sleep(0.25)
    result = {
        "cgroup": d,
        "memory_max": read(os.path.join(d, "memory.max")),
        "memory_peak_mb": round(int(read(os.path.join(d, "memory.peak"), "0") or 0) / mb, 1),
        "events": kv(os.path.join(d, "memory.events")),
        "overall_max_anon_mb": max((p["max_anon_mb"] for p in phases.values()), default=0),
        "overall_max_current_mb": max((p["max_current_mb"] for p in phases.values()), default=0),
        "phases": phases,
        "timeline_every_2s": timeline,
    }
    json.dump(result, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main()
