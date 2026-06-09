# Hosted Phase 1 Compute + Database Options for Aurelia

> **For Hermes:** Use subagent-driven-development skill to implement the selected path task-by-task.

**Goal:** Move Aurelia Phase 1 off Colab and off our own hardware onto cheap, reliable hosted CPU compute with a durable database/artifact layer.

**Architecture:** Treat Phase 1 as a CPU/SQLite workload, not a GPU workload. Keep the simulation runner close to a local writable disk for fast SQLite mutation, then stream compact summaries/events to a reliable external database and upload full artifacts to object storage.

**Tech Stack Candidates:** Dockerized Python runner, cheap CPU VM or CPU job runner, local SQLite working DB, D1/Turso/Postgres for queryable summaries, R2/S3/GCS for artifacts, Litestream/restic/rclone for backups.

---

## Current Aurelia Constraints

- Phase 1 is Python + SQLite + JSON + random sampling.
- It does not benefit materially from GPU/VRAM.
- The Colab problem is cost/overhead/reliability, not lack of GPU.
- Live SQLite must run on local disk, not Google Drive/FUSE.
- The current fast-monthly path uses 12 ticks/year instead of 360 ticks/year:
  - 200 years × 12 ticks/year = 2,400 ticks/world.
  - 5 worlds = 12,000 world ticks.
- For summary storage, the data volume is small:
  - Yearly summaries: 5 worlds × 200 years = 1,000 rows.
  - Monthly summaries: 5 × 200 × 12 = 12,000 rows.
  - Current NPC state at 120K NPCs is likely hundreds of MB, not tens of GB.
- Existing repo has no Dockerfile/requirements lock yet; deployment will need a containerization pass.

---

## Recommendation

### Best near-term architecture

Run the simulation on a cheap CPU host with a local SQLite working set:

```text
Dockerized Python runner
  ↓ local NVMe/persistent volume
5 SQLite world DBs
  ↓ every year/month
D1/Turso/Postgres summaries + event index
  ↓ final/checkpoints
R2/S3/GCS full artifacts (.db.zst, yearly_events.json, snapshots)
```

This avoids Colab entirely and keeps the hot simulation path on local disk.

### Best default provider choice

For always-on or near-continuous live simulation:

1. **DigitalOcean Droplet or Hetzner/Fly-class VM**
   - Simple.
   - Cheap monthly floor.
   - Local disk works for SQLite.
   - Easy to run systemd/supervisor and backups.

For scheduled 10–60 minute historical/batch runs:

1. **Google Cloud Run Jobs**
   - Clean managed job model.
   - Long timeout up to 168 hours.
   - Pay per run.
   - Use `/tmp` for live SQLite, upload results to GCS/R2.

2. **Modal CPU**
   - Best Python developer experience.
   - 24h timeout.
   - Native cron and volumes.
   - Slightly more expensive but low ops.

3. **AWS Batch/Fargate Spot**
   - Cheapest serious batch at scale.
   - More setup complexity.
   - Good if we later fan out many runs.

---

## Provider Findings

### DigitalOcean Droplet

Source: https://www.digitalocean.com/pricing/droplets

Observed pricing snippets:

- 2 GiB / 1 vCPU / 50GB SSD: $12/mo, $0.01786/hr.
- 4 GiB / 2 vCPU / 80GB SSD: $24/mo, $0.03571/hr.
- 8 GiB / 4 vCPU / 160GB SSD: $48/mo, $0.07143/hr.

Fit:

- Strong for an always-on live sim.
- Local SSD is good for SQLite.
- Simplest operational path: Docker Compose + systemd + nightly artifact upload.
- Cost predictable: roughly $24/mo for 2vCPU/4GB, $48/mo for 4vCPU/8GB.

Caveat:

- Self-managed backups/monitoring unless we build them.

### Fly Machines

Sources:

- https://fly.io/docs/about/pricing/
- https://fly.io/docs/volumes/overview/
- https://fly.io/docs/machines/overview/

Observed pricing/limits from docs:

- Example shared-cpu-1x / 2GB around $0.0154/hr in prior scrape.
- Rootfs for stopped machines: $0.15/GB/month.
- Volumes: $0.15/GB/month.
- Volumes are local persistent storage and attach to one machine.

Fit:

- Good for a containerized live sim.
- Good if we want to start/stop Machines programmatically.
- Better than serverless for a long-running process.

Caveat:

- Volumes are not shared/network storage; backup/replication is on us.

### Google Cloud Run Jobs

Sources:

- https://cloud.google.com/run/pricing
- https://cloud.google.com/run/docs/create-jobs
- https://cloud.google.com/run/docs/configuring/jobs/cloud-storage-volume-mounts

Observed limits:

- Default task timeout: 10 minutes.
- Maximum task timeout: 168 hours / 7 days.
- Jobs use instance-based billing with a 1-minute minimum.
- Supports Cloud Storage volume mounts and NFS volumes.

Cost estimate using documented us-central1 base rates from scrape:

- 2 vCPU + 4 GiB: about $0.158/hr.
- One 1-hour run/day: about $4.75/mo.
- 24/7 equivalent: about $115/mo.

Fit:

- Excellent for scheduled 10–60 minute historical runs.
- Not the best for a forever-running live sim.
- Use `/tmp` for live SQLite and upload artifacts to GCS/R2 at completion.

### Modal CPU

Sources:

- https://modal.com/pricing
- https://modal.com/docs/guide/timeouts
- https://modal.com/docs/guide/volumes
- https://modal.com/docs/guide/cron

Observed pricing/limits:

- CPU physical core: $0.0000131/core/sec.
- Memory: $0.00000222/GiB/sec.
- Function timeout configurable from 1 second to 24 hours.
- Native cron and volumes.

Cost estimate:

- 2 physical cores + 4 GiB: about $0.126/hr.
- One 1-hour run/day: about $3.79/mo.
- 24/7 equivalent: about $92/mo.

Fit:

- Best developer experience for Python batch.
- Good for scheduled fast-monthly runs.
- Not as cheap as a small VM for continuous operation.

### AWS Batch / Fargate Spot

Sources:

- https://aws.amazon.com/fargate/pricing/
- https://docs.aws.amazon.com/batch/latest/userguide/job_timeouts.html
- https://docs.aws.amazon.com/batch/latest/userguide/efs-volumes.html

Observed pricing/limits:

- us-east-1 Linux/x86 Fargate example: CPU $0.000011244/vCPU-sec, memory $0.000001235/GB-sec.
- AWS says Fargate Spot can be up to 70% cheaper than regular Fargate.
- AWS Batch has no default timeout and no maximum timeout value, though Fargate jobs should not be expected to run more than 14 days.
- EFS volumes supported.

Cost estimate:

- 2 vCPU + 4 GB on-demand: about $0.099/hr.
- One 1-hour run/day: about $2.96/mo.
- At 70% Spot discount: about $0.030/hr.

Fit:

- Best for cheap, serious batch once AWS complexity is acceptable.
- Good future path if we fan out many simulation variants.

Caveat:

- More infra complexity than Cloud Run or Modal.

### Railway

Sources:

- https://railway.com/pricing
- https://docs.railway.com/cron-jobs
- https://docs.railway.com/reference/volumes

Observed pricing/limits:

- Hobby plan $5 minimum usage, includes $5 usage credits.
- Pro plan $20 minimum usage.
- Pricing page shows usage-based CPU/memory and volume storage.
- Cron jobs may skip overlapping runs rather than terminating prior runs.

Cost estimate using scraped usage rates:

- 2 vCPU + 4GB: about $0.111/hr.
- One 1-hour run/day: about $3.34/mo before plan floor.

Fit:

- Easy PaaS route if we accept platform floor and cron semantics.
- Good for simple service + attached volume.

Caveat:

- Overlap-skipping is risky if a run stalls.

### Render Cron Jobs

Sources:

- https://render.com/docs/cronjobs
- https://render.com/pricing

Observed limits:

- Cron jobs stop after 12 hours.
- Cron jobs cannot provision or access a persistent disk.
- Minimum monthly charge of $1 per cron job service.

Fit:

- Acceptable for fire-and-forget batch if artifacts go directly to object storage/DB.
- Not suitable for local persistent SQLite as a working set.

### GitHub Actions

Sources:

- https://docs.github.com/en/actions/reference/limits
- https://docs.github.com/en/actions/reference/actions-minute-multipliers

Observed limits/pricing:

- GitHub-hosted runner max job execution: 6 hours.
- Linux private hosted runner baseline: $0.006/min = $0.36/hr.

Fit:

- Convenient for repo-native smoke tests and occasional public-repo jobs.
- Bad cost for frequent private heavy simulation.

---

## Database Options

### Option A — SQLite remains authoritative + event stream database

Best first move.

Hot path:

```text
local SQLite on the compute host
```

External durable path:

```text
D1/Turso/Postgres rows for summaries/events
R2/S3/GCS for full DBs and snapshots
```

Pros:

- Minimal code rewrite.
- Preserves current working mechanics.
- Cheapest and fastest path to reliability.
- External DB stays small and queryable.

Cons:

- Full NPC state is not natively queryable in external DB until snapshots are loaded or indexed.

### Option B — Turso/libSQL as hosted SQLite-compatible database

Source: https://turso.tech/pricing

Observed pricing:

- Free: 5GB storage, 500M rows read/month, 10M rows written/month.
- Developer: $4.99/mo, 9GB included + $0.75/GB, 25M rows written + $1/M overage.
- Scaler: $24.92/mo, 24GB included, 100M rows written.

Fit:

- Interesting because Aurelia already thinks in SQLite.
- Good for summaries/events and possibly current state tables.
- Remote write latency may hurt if used inside the inner tick loop.

Recommendation:

- Use Turso for event/snapshot/query DB, not for every tick mutation, unless we explicitly benchmark libSQL batching.

### Option C — Cloudflare D1 + R2

Sources:

- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/durable-objects/platform/limits/

Observed limits:

- D1 paid database size: 10GB per DB.
- D1 paid account storage: 1TB.
- D1 reads per Worker invocation: 1,000.
- D1 database is single-threaded for each individual DB.
- SQLite-backed Durable Object storage: 10GB per object on Workers Paid.
- Durable Object CPU/request: 30 seconds default, configurable to 5 minutes active CPU.

Fit:

- Excellent dashboard/API/event plane.
- Not a good primary compute host for current Python sim.
- Good if each run/world gets its own D1 DB or partitioned event tables.

Recommendation:

- Use D1 for run summaries, event index, dashboard queries.
- Use R2 for DB artifacts.

### Option D — Supabase/Postgres

Source: https://supabase.com/pricing

Observed pricing:

- Pro starts at $25/mo.
- Includes 8GB disk/project, additional disk $0.125/GB.
- Includes 100GB file storage, additional storage $0.0213/GB.

Fit:

- Strong if we want relational analytics, auth, realtime dashboard, and SQL tooling.
- More expensive floor than D1/Turso/cheap SQLite.

Recommendation:

- Use if dashboard/API sophistication matters more than lowest cost.

### Option E — Neon Postgres

Source: https://neon.tech/pricing

Observed pricing:

- Free: 0.5GB storage/project, 100 CU-hours monthly/project.
- Launch usage-based: $0.106/CU-hour, $0.35/GB-month, starts around $15/mo examples.

Fit:

- Good serverless Postgres option for summaries/events.
- Less compelling than D1/Turso if Cloudflare is already the dashboard layer.

---

## Concrete Deployment Shapes

### Shape 1 — Cheapest reliable continuous sim

```text
DigitalOcean 2vCPU/4GB or Fly Machine
Docker Compose
local SQLite world DBs on persistent disk
Litestream/restic/rclone backups every N minutes
Cloudflare D1/Turso for yearly/monthly summaries
R2/S3 for .db.zst artifacts
```

Estimated floor:

- DigitalOcean 2vCPU/4GB: $24/mo.
- R2/D1/Turso event layer likely small for summary-scale data.

Use when:

- We want a consistent always-running stream.
- We want low ops and low monthly cost.

### Shape 2 — Cheapest scheduled historical batch

```text
Google Cloud Run Job or AWS Batch/Fargate Spot
/tmp local SQLite during run
emit summaries to D1/Turso/Postgres
upload final artifacts to R2/GCS/S3
scale to zero between runs
```

Estimated 2vCPU/4GB one-hour daily cost:

- Cloud Run Jobs: about $4.75/mo.
- AWS Fargate on-demand: about $2.96/mo.
- AWS Fargate Spot example at 70% discount: about $0.89/mo.

Use when:

- We need periodic 200-year runs, not a continuous world.
- We want no always-on VM cost.

### Shape 3 — Best Python developer experience

```text
Modal CPU scheduled function
Modal Volume for workspace/artifacts
Turso/D1/Postgres for summaries
R2/S3 for final artifacts
```

Estimated 2 physical cores + 4GiB one-hour daily cost:

- About $3.79/mo.

Use when:

- We want the fastest implementation and easiest Python packaging.
- We accept slightly higher compute cost to reduce infrastructure burden.

### Shape 4 — Cloudflare-first data plane, external compute

```text
any CPU host/job runner
POST signed batches to Cloudflare Worker
Queue consumer writes D1
R2 stores artifacts
Durable Object fans out live stream
Pages dashboard
```

Use when:

- We want Cloudflare as the reliable public-facing system.
- Compute provider may change later.

This composes with Shapes 1–3.

---

## Immediate MVP Recommendation

Build Shape 1 + Shape 4:

```text
DigitalOcean/Fly-class CPU VM
+ local SQLite
+ Cloudflare Worker/D1/R2 stream
```

Why:

- Lowest cognitive load.
- Lowest continuous monthly floor.
- Preserves current code.
- Allows a live stream/database immediately.
- Lets us later swap compute host without changing the dashboard/data layer.

MVP steps:

1. Add `Dockerfile` and pinned Python dependencies.
2. Add `aurelia-runner` CLI wrapper:
   - `run-live`
   - `run-batch`
   - `emit-cloudflare`
   - `checkpoint`
3. Add SQLite backup/artifact compression:
   - `.db.zst` or `.db.gz` per world.
4. Add signed batch emitter:
   - POST yearly/monthly summaries to Cloudflare Worker.
   - Spool failed batches locally for replay.
5. Provision cheap VM with persistent disk.
6. Run via systemd.
7. Add Cloudflare Worker + D1 schema + R2 bucket.
8. Add dashboard after data is flowing.

---

## Decision Gate

Before implementing, choose one:

1. **Always-on live world:** VM/Fly + local SQLite + Cloudflare stream.
2. **Scheduled historical runs:** Cloud Run Jobs/Modal/AWS Batch + object storage.
3. **Pure Cloudflare data plane first:** add emitter + Worker/D1/R2 while still running anywhere.

My recommendation: implement #3 first because it makes the compute host swappable, then deploy #1 for the cheapest stable live runner.
