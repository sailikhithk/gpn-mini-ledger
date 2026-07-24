"""
Generate all architecture diagrams for GPN Mini Ledger README.
Uses the Python `diagrams` package (mingrammer/diagrams) with AWS + on-prem icons.
Outputs PNG files in docs/diagrams/.
"""
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

# Dark mode graph attributes
DARK_ATTR = {
    "bgcolor": "white",
    "fontcolor": "#1f2328",
    "fontsize": "14",
    "pad": "0.5",
    "ranksep": "1.0",
    "nodesep": "0.8",
}

NODE_ATTR = {
    "fontcolor": "#1f2328",
    "fontsize": "12",
}


def diagram_01_system_context():
    from diagrams import Diagram, Cluster, Edge
    from diagrams.onprem.client import Users, Client
    from diagrams.onprem.compute import Server
    from diagrams.onprem.database import PostgreSQL
    from diagrams.onprem.inmemory import Redis
    from diagrams.aws.storage import S3

    with Diagram(
        "System Context",
        filename=os.path.join(OUT_DIR, "01-system-context"),
        show=False,
        direction="TB",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        merchant = Client("Merchant")
        cardholder = Client("Cardholder")
        interviewer = Users("Capital One\nInterviewer")

        with Cluster("GPN Mini Ledger"):
            gateway = Server("API Gateway\n(Edge Switch)")
            ledger = Server("Ledger Core\n(CP - Strong Consistency)")
            outbox = Server("Outbox Worker\n(BASE - Eventual)")

        with Cluster("Local Infrastructure (Docker)"):
            postgres = PostgreSQL("PostgreSQL 16\nSERIALIZABLE + Flyway")
            redis = Redis("Redis 7\nIdempotency cache")
            localstack = S3("LocalStack\nS3 - SQS - DynamoDB")

        cardholder >> Edge(label="payment") >> merchant
        merchant >> Edge(label="authorize / capture / refund") >> gateway
        gateway >> Edge(label="ledger write") >> ledger
        ledger >> Edge(label="publish event") >> outbox
        ledger >> postgres
        gateway >> redis
        outbox >> postgres
        outbox >> localstack
        interviewer >> Edge(style="dashed", label="clone + verify") >> ledger


def diagram_02_layered_priority_stack():
    from diagrams import Diagram, Cluster, Edge
    from diagrams.onprem.compute import Server

    with Diagram(
        "Layered Priority Stack",
        filename=os.path.join(OUT_DIR, "02-layered-priority-stack"),
        show=False,
        direction="LR",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        with Cluster("Layer 1 - Core Ledger (CP)"):
            l1 = [
                Server("Correctness"),
                Server("Durability"),
                Server("Consistency"),
                Server("Auditability"),
                Server("Availability"),
            ]
            for i in range(len(l1) - 1):
                l1[i] >> l1[i + 1]

        with Cluster("Layer 2 - Edge Switch (AP)"):
            l2 = [
                Server("Latency"),
                Server("Availability (AP)"),
                Server("Idempotency"),
                Server("Fail-safe"),
            ]
            for i in range(len(l2) - 1):
                l2[i] >> l2[i + 1]

        with Cluster("Layer 3 - Async Lane (BASE)"):
            l3 = [
                Server("Throughput"),
                Server("Durability (BASE)"),
                Server("At-least-once"),
                Server("Reconciliation"),
            ]
            for i in range(len(l3) - 1):
                l3[i] >> l3[i + 1]

        l1[-1] >> Edge(label="wins on conflict", style="dashed") >> l2[0]
        l2[-1] >> Edge(label="wins on conflict", style="dashed") >> l3[0]


def diagram_03_module_map():
    from diagrams import Diagram, Cluster, Edge
    from diagrams.onprem.compute import Server
    from diagrams.onprem.database import PostgreSQL
    from diagrams.onprem.inmemory import Redis
    from diagrams.aws.storage import S3

    with Diagram(
        "Module Map",
        filename=os.path.join(OUT_DIR, "03-module-map"),
        show=False,
        direction="TB",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        with Cluster("Layer 1 - Core Ledger"):
            ledger_core = Server("ledger-core\nLedgerService - JournalEntry\nAccount - AuthorizationHold")
            audit_chain = Server("audit-chain (planned)\nSHA-256 hash chain")

        with Cluster("Layer 2 - Edge Switch"):
            api_gateway = Server("api-gateway\nRequest routing\nRate limiting")
            idempotency = Server("idempotency (planned)\nRedis + Postgres\ntwo-layer")
            orchestrator = Server("orchestrator (planned)\nPaymentSaga\ncompensation")
            fraud = Server("fraud-degradation (planned)\nfail-safe (not fail-open)")

        with Cluster("Layer 3 - Async Lane"):
            outbox = Server("outbox\nSKIP LOCKED claim\nstale reclaim")
            reconciliation = Server("reconciliation (planned)\nfingerprinted dedup")
            webhook = Server("webhook (planned)\nHMAC + replay protection")

        with Cluster("Data Stores"):
            postgres = PostgreSQL("PostgreSQL 16")
            redis = Redis("Redis 7")
            s3 = S3("LocalStack S3")

        api_gateway >> ledger_core
        api_gateway >> idempotency
        ledger_core >> postgres
        ledger_core >> outbox
        outbox >> postgres
        idempotency >> redis
        idempotency >> postgres
        audit_chain >> postgres
        audit_chain >> s3
        orchestrator >> ledger_core
        orchestrator >> fraud
        outbox >> webhook
        reconciliation >> postgres


def diagram_04_request_flow():
    from diagrams import Diagram, Cluster, Edge
    from diagrams.onprem.client import Client
    from diagrams.onprem.compute import Server
    from diagrams.onprem.database import PostgreSQL

    with Diagram(
        "Request Flow - Capture Sequence",
        filename=os.path.join(OUT_DIR, "04-request-flow"),
        show=False,
        direction="TB",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        merchant = Client("Merchant")
        gateway = Server("API Gateway")
        ledger = Server("LedgerService")
        postgres = PostgreSQL("PostgreSQL\n(SERIALIZABLE)")
        outbox = Server("Outbox Worker")
        webhook = Server("Webhook (planned)")

        merchant >> Edge(label="1. POST /capture") >> gateway
        gateway >> Edge(label="2. Validate") >> gateway
        gateway >> Edge(label="3. capture()") >> ledger

        with Cluster("Layer 1 - CP (strong consistency)"):
            ledger >> Edge(label="4. BEGIN SERIALIZABLE") >> postgres
            ledger >> Edge(label="5. SELECT auth_hold FOR UPDATE") >> postgres
            ledger >> Edge(label="6. CHECK: captured + amount <= authorized") >> postgres
            ledger >> Edge(label="7. INSERT journal_entry + lines + outbox_event") >> postgres
            ledger >> Edge(label="8. COMMIT") >> postgres
            postgres >> Edge(label="9. 40001 conflict (retry 10x)", style="dashed") >> ledger

        ledger >> Edge(label="10. LedgerEntryResult") >> gateway
        gateway >> Edge(label="11. 200 OK") >> merchant

        with Cluster("Layer 3 - BASE (eventual)"):
            outbox >> Edge(label="12. SELECT SKIP LOCKED") >> postgres
            postgres >> Edge(label="13. claimed events") >> outbox
            outbox >> Edge(label="14. POST event (HMAC)") >> webhook
            webhook >> Edge(label="15. 200 OK") >> outbox
            outbox >> Edge(label="16. UPDATE published = true") >> postgres


def diagram_05_data_model():
    from diagrams import Diagram, Edge
    from diagrams.onprem.database import PostgreSQL

    with Diagram(
        "Data Model ERD",
        filename=os.path.join(OUT_DIR, "05-data-model"),
        show=False,
        direction="LR",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        account = PostgreSQL("ACCOUNT\nid: uuid PK\ncode: string\ntype: AccountType\ncurrency: string\nbalance_minor: bigint")
        journal_entry = PostgreSQL("JOURNAL_ENTRY\nid: uuid PK\nauthorization_id: uuid FK\ntype: EntryType\ncurrency: string\namount_minor: bigint\nidempotency_key: string UK\ncreated_at: timestamp")
        journal_line = PostgreSQL("JOURNAL_LINE\nid: uuid PK\njournal_entry_id: uuid FK\naccount_id: uuid FK\nside: DEBIT/CREDIT\namount_minor: bigint")
        auth_hold = PostgreSQL("AUTHORIZATION_HOLD\nid: uuid PK\nauthorization_id: uuid UK\nmerchant_id: uuid\ncurrency: string\nauthorized_minor: bigint\ncaptured_minor: bigint\nrefunded_minor: bigint\nstatus: string\ncreated_at: timestamp")

        account >> Edge(label="posts to") >> journal_line
        journal_entry >> Edge(label="contains") >> journal_line
        auth_hold >> Edge(label="produces") >> journal_entry


def diagram_06_concurrency_retry():
    from diagrams import Diagram, Edge
    from diagrams.onprem.compute import Server
    from diagrams.generic.storage import Storage
    from diagrams.generic.compute import Rack

    with Diagram(
        "Concurrency - SERIALIZABLE + Retry",
        filename=os.path.join(OUT_DIR, "06-concurrency-retry"),
        show=False,
        direction="TB",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        start = Server("capture() called")
        check_idem = Server("Idempotency key\nseen before?")
        return_existing = Server("Return cached result\n(exactly-once)")
        begin_tx = Server("BEGIN SERIALIZABLE")
        read_auth = Server("SELECT auth_hold\nFOR UPDATE")
        check_budget = Server("captured + amount\n<= authorized?")
        rollback = Server("ROLLBACK")
        exceeds_error = Server("throw\nCaptureExceedsAuthorizationException")
        write_entry = Server("INSERT journal_entry\n+ journal_lines\n+ outbox_event")
        commit = Server("COMMIT")
        return_success = Server("Return LedgerEntryResult")
        retry = Server("attempts < maxRetries?")
        backoff = Server("sleep backoffMs * 2^attempt\n(exponential)")
        propagate = Server("throw ConcurrencyFailureException\n(retried 10x, still contended)")

        start >> check_idem
        check_idem >> Edge(label="yes") >> return_existing
        check_idem >> Edge(label="no") >> begin_tx
        begin_tx >> read_auth
        read_auth >> check_budget
        check_budget >> Edge(label="no") >> rollback
        rollback >> exceeds_error
        check_budget >> Edge(label="yes") >> write_entry
        write_entry >> commit
        commit >> Edge(label="success") >> return_success
        commit >> Edge(label="40001 conflict") >> retry
        retry >> Edge(label="yes") >> backoff
        backoff >> begin_tx
        retry >> Edge(label="no") >> propagate


def diagram_07_cicd_pipeline():
    from diagrams import Diagram, Cluster, Edge
    from diagrams.onprem.compute import Server
    from diagrams.onprem.vcs import Git
    from diagrams.aws.devtools import Codebuild as CodeBuild

    with Diagram(
        "CI/CD Pipeline",
        filename=os.path.join(OUT_DIR, "07-cicd-pipeline"),
        show=False,
        direction="LR",
        graph_attr=DARK_ATTR,
        node_attr=NODE_ATTR,
    ):
        with Cluster("Pull Request"):
            branch = Server("Branch Naming")
            pr_lint = Server("PR Lint\nConventional Commits")
            labeler = Server("Labeler\n+ Size Labeler")
            anti_pattern = Server("Anti-Pattern Scan\n(advisory)")
            copilot = Server("Copilot Review\n(advisory)")

        with Cluster("Blocking Gates"):
            ci = CodeBuild("CI\nBuild + Test (JDK 25)")
            migration = Server("Migration Check\n6 Flyway checks")
            codeql = Server("CodeQL\nstatic analysis")

        with Cluster("Release"):
            squash = Git("Squash Merge\nto main")
            release_wf = Server("release.yml\nauto-tag + GitHub Release")
            stale = Server("stale-branches.yml\nweekly cleanup")
            dependabot = Server("dependabot.yml\nweekly dependency PRs")

        branch >> ci
        pr_lint >> ci
        labeler >> ci
        anti_pattern >> Edge(style="dashed") >> ci
        copilot >> Edge(style="dashed") >> ci

        ci >> migration
        migration >> codeql
        codeql >> squash
        squash >> release_wf
        release_wf >> Edge(style="dashed") >> stale
        release_wf >> Edge(style="dashed") >> dependabot


if __name__ == "__main__":
    print("Generating diagrams...")
    diagram_01_system_context()
    print("  01-system-context.png")
    diagram_02_layered_priority_stack()
    print("  02-layered-priority-stack.png")
    diagram_03_module_map()
    print("  03-module-map.png")
    diagram_04_request_flow()
    print("  04-request-flow.png")
    diagram_05_data_model()
    print("  05-data-model.png")
    diagram_06_concurrency_retry()
    print("  06-concurrency-retry.png")
    diagram_07_cicd_pipeline()
    print("  07-cicd-pipeline.png")
    print("Done. Files in docs/diagrams/")
