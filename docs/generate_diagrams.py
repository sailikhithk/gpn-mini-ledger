"""
Generate all architecture diagrams for GPN Mini Ledger README.
Uses the Python `diagrams` package (mingrammer/diagrams) with AWS + on-prem icons.

Layout strategy:
- direction="TB" for all diagrams so clusters become horizontal rows stacked vertically.
- Within each cluster, nodes are ordered left-to-right using invisible `constraint="false"` edges.
- This produces clean, square-ish diagrams that look like a human drew them.
"""
import os
from diagrams import Diagram, Cluster, Edge, Node

OUT_DIR = os.path.join(os.path.dirname(__file__), "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)


def graph_attrs(size: str = "10,10") -> dict:
    return {
        "bgcolor": "white",
        "fontcolor": "#1f2328",
        "fontsize": "14",
        "pad": "0.3",
        "ranksep": "1.0",
        "nodesep": "0.7",
        "splines": "ortho",
        "compound": "true",
        "ratio": "fill",
        "dpi": "130",
        "size": size,
    }


NODE_ATTR = {
    "fontcolor": "#1f2328",
    "fontsize": "11",
}


def hrow(nodes):
    """Arrange nodes left-to-right in the same rank without drawing visible edges."""
    for i in range(len(nodes) - 1):
        nodes[i] >> Edge(style="invis", constraint="false") >> nodes[i + 1]


def vlink(src, dst, label=None, style="solid"):
    """Visible vertical link between layers/clusters."""
    kwargs = {"style": style}
    if label:
        kwargs["label"] = label
    src >> Edge(**kwargs) >> dst


def layer_link(src, dst, src_cluster, dst_cluster, label=None, style="dashed"):
    """Draw an arrow clipped to the boundaries of two clusters."""
    kwargs = {
        "style": style,
        "ltail": f"cluster_{src_cluster}",
        "lhead": f"cluster_{dst_cluster}",
    }
    if label:
        kwargs["label"] = label
    src >> Edge(**kwargs) >> dst


def snake_row(cluster_name, node_makers):
    """
    Create a row of nodes inside a Cluster that reads left-to-right.
    node_makers is a list of callables that return a node instance.
    Returns the list of created nodes.
    """
    nodes = []
    with Cluster(cluster_name):
        for make_node in node_makers:
            nodes.append(make_node())
    # order left-to-right (invisible, non-constraining)
    for i in range(len(nodes) - 1):
        nodes[i] >> Edge(style="invis", constraint="false") >> nodes[i + 1]
    return nodes


def snake_arrows(nodes):
    """Draw visible horizontal arrows across a row without changing rank."""
    for i in range(len(nodes) - 1):
        nodes[i] >> Edge(constraint="false") >> nodes[i + 1]


def snake_drop(prev_left, next_left, prev_right, next_right, label=None):
    """
    Align two rows vertically and draw a flow arrow from the end of the
    previous row to the start of the next row.
    """
    prev_left >> Edge(style="invis") >> next_left
    kwargs = {"constraint": "false"}
    if label:
        kwargs["label"] = label
    prev_right >> Edge(**kwargs) >> next_right


# ------------------------------------------------------------------------------
# 01. System Context
# ------------------------------------------------------------------------------
def diagram_01_system_context():
    from diagrams.onprem.client import Client, Users
    from diagrams.aws.network import APIGateway
    from diagrams.programming.framework import Spring
    from diagrams.aws.integration import SQS, SNS
    from diagrams.onprem.database import PostgreSQL
    from diagrams.onprem.inmemory import Redis
    from diagrams.aws.storage import S3
    from diagrams.onprem.ci import GithubActions

    DMS_BG = "#101010"
    DMS_PANEL = "#1a1a1a"
    DMS_ACCENT = "#0078d4"
    DMS_FONT = "#ffffff"
    DMS_EDGE = "#9ca3af"

    dms_graph = {
        "bgcolor": DMS_BG,
        "fontcolor": DMS_FONT,
        "fontsize": "14",
        "pad": "0.2",
        "ranksep": "0.7",
        "nodesep": "0.4",
        "splines": "ortho",
        "compound": "false",
        "ratio": "fill",
        "dpi": "130",
        "size": "14,10",
        "label": "GPN Mini Ledger",
        "labelloc": "t",
        "labeljust": "l",
    }
    dms_node = {
        "fontcolor": DMS_FONT,
        "fontsize": "12",
        "shape": "box",
        "style": "rounded",
        "fixedsize": "false",
        "labelloc": "b",
    }
    dms_edge = {"color": DMS_EDGE, "fontcolor": DMS_FONT}

    panel_attr = {
        "shape": "note",
        "style": "filled",
        "fillcolor": DMS_PANEL,
        "color": "#333333",
        "fontcolor": DMS_FONT,
        "fontsize": "12",
        "labelloc": "c",
        "width": "5.0",
        "height": "3.5",
        "fixedsize": "false",
    }

    def dms_note(text):
        return Node(text, **panel_attr)

    with Diagram(
        "",
        filename=os.path.join(OUT_DIR, "01-system-context"),
        show=False,
        direction="LR",
        graph_attr=dms_graph,
        node_attr=dms_node,
        edge_attr=dms_edge,
    ):
        with Cluster(
            "External Actors",
            graph_attr={
                "bgcolor": DMS_PANEL,
                "pencolor": "#555555",
                "fontcolor": "white",
            },
        ):
            cardholder = Client("Cardholder")
            merchant = Client("Merchant")
            interviewer = Users("Capital One\nInterviewer")
            hrow([cardholder, merchant, interviewer])

        with Cluster(
            "GPN Mini Ledger",
            graph_attr={
                "bgcolor": DMS_PANEL,
                "pencolor": "#777777",
                "fontcolor": "white",
            },
        ):
            gateway = APIGateway("API Gateway\n(Edge Switch)")
            ledger = Spring("Ledger Core\n(CP - Strong Consistency)")
            outbox = SQS("Outbox Worker\n(BASE - Eventual)")
            sns = SNS("Webhook\nNotifier")
            hrow([gateway, ledger, outbox, sns])

            postgres = PostgreSQL("PostgreSQL 16\nSERIALIZABLE + Flyway")
            redis = Redis("Redis 7\nIdempotency cache")
            s3 = S3("LocalStack S3\nObject Storage")
            hrow([postgres, redis, s3])

        with Cluster(
            "CI/CD",
            graph_attr={
                "bgcolor": DMS_PANEL,
                "pencolor": "#555555",
                "fontcolor": "white",
            },
        ):
            github = GithubActions("GitHub Actions")

        notes = dms_note(
            "Flow\n"
            "- Cardholder pays Merchant\n"
            "- Merchant posts authorize / capture / refund\n"
            "- API Gateway routes to Ledger Core\n"
            "- Core writes PostgreSQL + outbox\n"
            "- SNS webhook returns 200 OK\n\n"
            "Authentication / Idempotency\n"
            "- Redis caches idempotency keys\n"
            "- prevents duplicate capture / refund\n\n"
            "Legend\n"
            "1. API Gateway (Edge Switch)\n"
            "2. Ledger Core (CP - Strong Consistency)\n"
            "3. Outbox Worker (BASE - Eventual)\n"
            "4. PostgreSQL 16 (SERIALIZABLE + Flyway)\n"
            "5. Redis 7 (Idempotency cache)\n"
            "6. LocalStack S3 (Object Storage)\n"
            "7. SNS Webhook Notifier\n"
            "8. GitHub Actions (CI/CD)"
        )

        cardholder >> Edge(label="payment") >> merchant
        merchant >> Edge(label="authorize / capture / refund") >> gateway
        gateway >> Edge(label="ledger write") >> ledger
        ledger >> Edge(label="publish event") >> outbox
        outbox >> Edge(label="dispatch") >> sns
        sns >> Edge(style="dotted", label="200 OK / retry") >> merchant

        gateway >> Edge(style="dashed", label="cache check") >> redis
        ledger >> Edge(style="dashed") >> postgres
        ledger >> Edge(style="dashed") >> s3

        interviewer >> Edge(style="dotted", label="clone + verify") >> ledger
        github >> Edge(style="dashed", label="build + test") >> ledger

        # Push the Notes panel to the right of the system cluster.
        outbox >> Edge(style="invis") >> notes


# ------------------------------------------------------------------------------
# 02. Layered Priority Stack
# ------------------------------------------------------------------------------
def diagram_02_layered_priority_stack():
    from diagrams.programming.framework import Spring
    from diagrams.onprem.database import PostgreSQL
    from diagrams.aws.network import APIGateway
    from diagrams.onprem.inmemory import Redis
    from diagrams.aws.security import Shield
    from diagrams.aws.integration import SQS
    from diagrams.aws.storage import S3

    with Diagram(
        "Layered Priority Stack",
        filename=os.path.join(OUT_DIR, "02-layered-priority-stack"),
        show=False,
        direction="TB",
        graph_attr=graph_attrs(size="10,10"),
        node_attr=NODE_ATTR,
    ):
        with Cluster("Layer 1 - Core Ledger (CP)"):
            core = [
                Spring("Correctness"),
                PostgreSQL("Durability"),
                Spring("Consistency"),
                Shield("Auditability"),
                Spring("Availability"),
            ]
            hrow(core)

        with Cluster("Layer 2 - Edge Switch (AP)"):
            edge = [
                APIGateway("Latency"),
                APIGateway("Availability (AP)"),
                Redis("Idempotency"),
                Shield("Fail-safe"),
            ]
            hrow(edge)

        with Cluster("Layer 3 - Async Lane (BASE)"):
            async_ = [
                SQS("Throughput"),
                S3("Durability (BASE)"),
                SQS("At-least-once"),
                Spring("Reconciliation"),
            ]
            hrow(async_)

        # Connect layer boundaries so the arrow reads as whole-layer priority
        layer_link(
            core[0],
            edge[0],
            "Layer 1 - Core Ledger (CP)",
            "Layer 2 - Edge Switch (AP)",
            label="wins on conflict",
        )
        layer_link(
            edge[0],
            async_[0],
            "Layer 2 - Edge Switch (AP)",
            "Layer 3 - Async Lane (BASE)",
            label="wins on conflict",
        )


# ------------------------------------------------------------------------------
# 03. Module Map
# ------------------------------------------------------------------------------
def diagram_03_module_map():
    from diagrams.programming.framework import Spring
    from diagrams.aws.network import APIGateway
    from diagrams.onprem.inmemory import Redis
    from diagrams.aws.security import Shield, KMS
    from diagrams.aws.integration import SQS, SNS
    from diagrams.onprem.database import PostgreSQL
    from diagrams.aws.storage import S3

    with Diagram(
        "Module Map",
        filename=os.path.join(OUT_DIR, "03-module-map"),
        show=False,
        direction="TB",
        graph_attr=graph_attrs(size="12,11"),
        node_attr=NODE_ATTR,
    ):
        with Cluster("Layer 1 - Core Ledger"):
            ledger_core = Spring("ledger-core\nLedgerService")
            audit_chain = KMS("audit-chain\n(planned)")
            hrow([ledger_core, audit_chain])

        with Cluster("Layer 2 - Edge Switch"):
            api_gateway = APIGateway("api-gateway")
            idempotency = Redis("idempotency\n(planned)")
            orchestrator = Spring("orchestrator\n(planned)")
            fraud = Shield("fraud-degradation\n(planned)")
            hrow([api_gateway, idempotency, orchestrator, fraud])

        with Cluster("Layer 3 - Async Lane"):
            outbox = SQS("outbox\nSKIP LOCKED")
            webhook = SNS("webhook\n(planned)")
            reconciliation = Spring("reconciliation\n(planned)")
            hrow([outbox, webhook, reconciliation])

        with Cluster("Data Stores"):
            postgres = PostgreSQL("PostgreSQL 16")
            redis = Redis("Redis 7")
            s3 = S3("LocalStack S3")
            hrow([postgres, redis, s3])

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


# ------------------------------------------------------------------------------
# 04. Request Flow - Capture Sequence
# ------------------------------------------------------------------------------
def diagram_04_request_flow():
    from diagrams.onprem.client import Client
    from diagrams.aws.network import APIGateway
    from diagrams.programming.framework import Spring
    from diagrams.onprem.database import PostgreSQL
    from diagrams.aws.integration import SQS, SNS

    with Diagram(
        "Request Flow - Capture Sequence",
        filename=os.path.join(OUT_DIR, "04-request-flow"),
        show=False,
        direction="TB",
        graph_attr=graph_attrs(size="12,8"),
        node_attr=NODE_ATTR,
    ):
        # Row 1: Requester -> Edge Switch -> Core -> Database
        row1 = snake_row("1. Receive & Validate", [
            lambda: Client("Merchant"),
            lambda: APIGateway("API Gateway\n(Edge Switch)"),
            lambda: Spring("LedgerService\n(CP Core)"),
            lambda: PostgreSQL("PostgreSQL\nSERIALIZABLE"),
        ])
        snake_arrows(row1)

        # Row 2: Publish -> Outbox -> Webhook -> 200 OK
        row2 = snake_row("2. Persist & Dispatch", [
            lambda: PostgreSQL("COMMIT"),
            lambda: SQS("Outbox Worker"),
            lambda: SNS("Webhook"),
            lambda: Client("200 OK"),
        ])
        snake_arrows(row2)

        # Vertical drop from end of row 1 to start of row 2
        snake_drop(row1[0], row2[0], row1[-1], row2[0], label="publish event")

        # Retry loop: PostgreSQL detects conflict -> LedgerService retries
        row1[-1] >> Edge(label="40001 conflict\nretry 10x", style="dashed", constraint="false") >> row1[2]
        # 200 OK response path
        row2[2] >> Edge(label="200 OK", style="dotted", constraint="false") >> row2[-1]


# ------------------------------------------------------------------------------
# 05. Data Model ERD
# ------------------------------------------------------------------------------
def diagram_05_data_model():
    from diagrams.onprem.database import PostgreSQL

    with Diagram(
        "Data Model ERD",
        filename=os.path.join(OUT_DIR, "05-data-model"),
        show=False,
        direction="TB",
        graph_attr=graph_attrs(size="10,9"),
        node_attr=NODE_ATTR,
    ):
        with Cluster("Core Entities"):
            account = PostgreSQL("ACCOUNT\nPK: id, UK: code\nbalance_minor, type, currency")
            journal_entry = PostgreSQL("JOURNAL_ENTRY\nPK: id, UK: idempotency_key\ncurrency, amount_minor, created_at")
            hrow([account, journal_entry])

        with Cluster("Lines and Holds"):
            journal_line = PostgreSQL("JOURNAL_LINE\nPK: id, FK: entry_id, account_id\nside, amount_minor")
            auth_hold = PostgreSQL("AUTHORIZATION_HOLD\nPK: id, UK: authorization_id\nauthorized / captured / refunded, status, currency")
            hrow([journal_line, auth_hold])

        journal_entry >> Edge(label="contains") >> journal_line
        account >> Edge(label="posts to") >> journal_line
        auth_hold >> Edge(label="produces") >> journal_entry


# ------------------------------------------------------------------------------
# 06. Concurrency - SERIALIZABLE + Retry
# ------------------------------------------------------------------------------
def diagram_06_concurrency_retry():
    from diagrams.programming.framework import Spring
    from diagrams.onprem.database import PostgreSQL
    from diagrams.onprem.compute import Server

    with Diagram(
        "Concurrency - SERIALIZABLE + Retry",
        filename=os.path.join(OUT_DIR, "06-concurrency-retry"),
        show=False,
        direction="TB",
        graph_attr=graph_attrs(size="12,10"),
        node_attr=NODE_ATTR,
    ):
        # Row 1: capture -> idempotency check -> begin tx
        row1 = snake_row("1. Start & Idempotency", [
            lambda: Spring("capture() called"),
            lambda: Server("idempotency key\nseen before?"),
            lambda: PostgreSQL("BEGIN\nSERIALIZABLE"),
        ])
        snake_arrows(row1)

        # Row 2: SELECT auth_hold -> check budget -> INSERT
        row2 = snake_row("2. Core Transaction", [
            lambda: PostgreSQL("SELECT auth_hold\nFOR UPDATE"),
            lambda: Server("captured + amount\n<= authorized?"),
            lambda: PostgreSQL("INSERT entry +\nlines + outbox_event"),
        ])
        snake_arrows(row2)

        # Row 3: COMMIT -> success
        row3 = snake_row("3. Commit", [
            lambda: PostgreSQL("COMMIT"),
            lambda: Spring("return\nLedgerEntryResult"),
        ])
        snake_arrows(row3)

        # Vertical drops
        snake_drop(row1[0], row2[0], row1[-1], row2[0])
        snake_drop(row2[0], row3[0], row2[-1], row3[0])

        # Branches
        cached = Spring("return cached\nresult")
        exceeds = Spring("throw\nCaptureExceedsAuthException")
        retry = Spring("retry 10x\nexponential backoff")

        row1[1] >> Edge(xlabel="yes", style="dashed", constraint="false") >> cached
        row1[1] >> Edge(xlabel="no", style="dashed", constraint="false") >> row1[2]

        row2[1] >> Edge(xlabel="no", style="dashed", constraint="false") >> exceeds
        row2[1] >> Edge(xlabel="yes", style="dashed", constraint="false") >> row2[2]

        row3[0] >> Edge(xlabel="40001 conflict", style="dashed", constraint="false") >> retry
        retry >> Edge(style="dashed", constraint="false") >> row1[2]


# ------------------------------------------------------------------------------
# 07. CI/CD Pipeline
# ------------------------------------------------------------------------------
def diagram_07_cicd_pipeline():
    from diagrams.onprem.compute import Server
    from diagrams.onprem.vcs import Git
    from diagrams.onprem.database import PostgreSQL
    from diagrams.aws.devtools import Codebuild
    from diagrams.aws.security import Shield
    from diagrams.onprem.ci import GithubActions

    with Diagram(
        "CI/CD Pipeline",
        filename=os.path.join(OUT_DIR, "07-cicd-pipeline"),
        show=False,
        direction="TB",
        graph_attr=graph_attrs(size="14,9"),
        node_attr=NODE_ATTR,
    ):
        # Row 1: PR gates (all feed into CI)
        row1 = snake_row("1. Pull Request", [
            lambda: Git("Branch\nNaming"),
            lambda: GithubActions("PR Lint\nConventional Commits"),
            lambda: GithubActions("Labeler +\nSize Labeler"),
            lambda: GithubActions("Anti-Pattern\nScan (advisory)"),
            lambda: GithubActions("Copilot Review\n(advisory)"),
        ])

        # Row 2: Blocking gates
        row2 = snake_row("2. Blocking Gates", [
            lambda: Codebuild("CI\nBuild + Test"),
            lambda: PostgreSQL("Migration\nCheck"),
            lambda: Shield("CodeQL\nStatic Analysis"),
            lambda: Git("Squash Merge\nto main"),
        ])
        snake_arrows(row2)

        # Row 3: Release workflows
        row3 = snake_row("3. Release", [
            lambda: GithubActions("release.yml"),
            lambda: GithubActions("stale-branches.yml"),
            lambda: GithubActions("dependabot.yml"),
        ])
        # stale/dependabot are parallel, not sequential
        row3[0] >> Edge(style="dashed", constraint="false") >> row3[1]
        row3[0] >> Edge(style="dashed", constraint="false") >> row3[2]

        # Vertical drops align rows
        snake_drop(row1[0], row2[0], row1[-1], row2[0])
        snake_drop(row2[0], row3[0], row2[-1], row3[1], label="tag & release")


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
