# Infrastructure (milestone M4)

AWS CDK app (Python), planned stacks:

1. **DataStack:** S3 raw and curated buckets, Glue database + ETL job, Athena workgroup
2. **ToolsStack:** Lambda functions (read-only, parameterised Athena queries) registered as AgentCore Gateway targets
3. **AgentStack:** Strands agent container on AgentCore Runtime, with CloudWatch observability

All IAM roles follow least privilege. See `docs/ARCHITECTURE.md` for the design rationale.
