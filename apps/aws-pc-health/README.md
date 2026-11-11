# AWS & PC Health

A small local tool that reports the health of your PC (CPU, memory, disk,
battery, uptime) and your AWS account (EC2 state and status checks, firing
CloudWatch alarms, last-30-day cost).

```bash
pip install -r requirements.txt
python health.py            # both
python health.py --pc       # PC only
python health.py --aws --profile dev --region us-east-1 --json
```

Exit code: `0` healthy, `1` warning (>=80% or alarms), `2` critical (>=90% or failing checks).

AWS needs read-only permissions: `sts:GetCallerIdentity`, `ec2:DescribeInstances`,
`ec2:DescribeInstanceStatus`, `cloudwatch:DescribeAlarms`, `ce:GetCostAndUsage`.

Data stays on your machine. See [privacy-policy](privacy-policy/index.html).
