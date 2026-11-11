#!/usr/bin/env python3
"""AWS & PC Health - local health report.

Everything runs on your machine. Nothing is sent anywhere except read-only
API calls to AWS using credentials you already have configured.

Usage:
    python health.py                 # PC + AWS report
    python health.py --pc            # PC only
    python health.py --aws           # AWS only
    python health.py --json          # machine-readable output
    python health.py --profile dev --region us-east-1
Exit code: 0 = healthy, 1 = warnings, 2 = critical.
"""
import argparse
import json
import platform
import shutil
import sys
from datetime import datetime, timedelta, timezone

WARN, CRIT = 80.0, 90.0  # percent thresholds


def level(pct):
    return "critical" if pct >= CRIT else "warning" if pct >= WARN else "ok"


def pc_health():
    try:
        import psutil
    except ImportError:
        return {"error": "psutil not installed (pip install -r requirements.txt)"}
    vm = psutil.virtual_memory()
    checks = {
        "cpu": psutil.cpu_percent(interval=1),
        "memory": vm.percent,
        "disk": round(shutil.disk_usage("/").used / shutil.disk_usage("/").total * 100, 1),
    }
    out = {
        "host": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "uptime_hours": round((datetime.now().timestamp() - psutil.boot_time()) / 3600, 1),
        "checks": {k: {"percent": v, "status": level(v)} for k, v in checks.items()},
    }
    batt = getattr(psutil, "sensors_battery", lambda: None)()
    if batt:
        out["battery"] = {"percent": round(batt.percent), "plugged_in": batt.power_plugged}
    return out


def aws_health(profile=None, region=None):
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return {"error": "boto3 not installed (pip install -r requirements.txt)"}
    try:
        s = boto3.Session(profile_name=profile, region_name=region)
        ident = s.client("sts").get_caller_identity()
        out = {"account": ident["Account"], "region": s.region_name}

        ec2 = s.client("ec2")
        states = {}
        for page in ec2.get_paginator("describe_instances").paginate():
            for r in page["Reservations"]:
                for i in r["Instances"]:
                    st = i["State"]["Name"]
                    states[st] = states.get(st, 0) + 1
        out["ec2_instances"] = states

        bad = []
        for page in ec2.get_paginator("describe_instance_status").paginate(IncludeAllInstances=False):
            for i in page["InstanceStatuses"]:
                if i["InstanceStatus"]["Status"] not in ("ok", "not-applicable") or \
                   i["SystemStatus"]["Status"] not in ("ok", "not-applicable"):
                    bad.append(i["InstanceId"])
        out["ec2_failing_status_checks"] = bad

        cw = s.client("cloudwatch")
        alarms = [a["AlarmName"] for p in cw.get_paginator("describe_alarms").paginate(StateValue="ALARM")
                  for a in p["MetricAlarms"]]
        out["cloudwatch_alarms_firing"] = alarms

        ce = s.client("ce", region_name="us-east-1")
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=30)
        cost = ce.get_cost_and_usage(
            TimePeriod={"Start": str(start), "End": str(end)},
            Granularity="MONTHLY", Metrics=["UnblendedCost"])
        out["cost_last_30d_usd"] = round(sum(
            float(r["Total"]["UnblendedCost"]["Amount"]) for r in cost["ResultsByTime"]), 2)
        out["status"] = "critical" if bad else "warning" if alarms else "ok"
        return out
    except (BotoCoreError, ClientError) as e:
        return {"error": str(e)}


def render(rep):
    lines = []
    if "pc" in rep:
        pc = rep["pc"]
        lines.append("== PC health ==")
        if "error" in pc:
            lines.append(f"  ! {pc['error']}")
        else:
            lines.append(f"  {pc['host']} ({pc['os']}), up {pc['uptime_hours']}h")
            for k, v in pc["checks"].items():
                lines.append(f"  {k:<8}{v['percent']:>5}%  [{v['status']}]")
            if "battery" in pc:
                lines.append(f"  battery {pc['battery']['percent']}% (plugged in: {pc['battery']['plugged_in']})")
    if "aws" in rep:
        a = rep["aws"]
        lines.append("== AWS health ==")
        if "error" in a:
            lines.append(f"  ! {a['error']}")
        else:
            lines.append(f"  account {a['account']} / {a['region']}  [{a['status']}]")
            lines.append(f"  EC2 instances: {a['ec2_instances'] or 'none'}")
            lines.append(f"  failing status checks: {a['ec2_failing_status_checks'] or 'none'}")
            lines.append(f"  firing alarms: {a['cloudwatch_alarms_firing'] or 'none'}")
            lines.append(f"  cost, last 30 days: ${a['cost_last_30d_usd']}")
    return "\n".join(lines)


def exit_code(rep):
    statuses = []
    if "checks" in rep.get("pc", {}):
        statuses += [c["status"] for c in rep["pc"]["checks"].values()]
    if "status" in rep.get("aws", {}):
        statuses.append(rep["aws"]["status"])
    return 2 if "critical" in statuses else 1 if "warning" in statuses else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pc", action="store_true")
    p.add_argument("--aws", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--profile")
    p.add_argument("--region")
    a = p.parse_args()
    both = not (a.pc or a.aws)
    rep = {}
    if a.pc or both:
        rep["pc"] = pc_health()
    if a.aws or both:
        rep["aws"] = aws_health(a.profile, a.region)
    print(json.dumps(rep, indent=2) if a.json else render(rep))
    sys.exit(exit_code(rep))


if __name__ == "__main__":
    main()
