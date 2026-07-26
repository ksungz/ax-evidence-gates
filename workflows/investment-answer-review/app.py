"""Streamlit review surface for the LangGraph investment-answer workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_SRC = Path(__file__).resolve().parent / "src"
GATE_SRC = REPO_ROOT / "gates" / "investment-answer" / "src"
EXAMPLES = GATE_SRC / "examples"
sys.path.insert(0, str(WORKFLOW_SRC))
sys.path.insert(0, str(GATE_SRC))

from langgraph.types import Command  # noqa: E402

from investment_review_workflow import (  # noqa: E402
    build_review_graph,
    get_interrupt_payload,
)


EXAMPLE_OPTIONS = {
    "위험 표현이 있는 투자 답변": EXAMPLES / "bad-answer.md",
    "검사를 통과하는 개선 답변": EXAMPLES / "better-answer.md",
    "주문장애 안내": EXAMPLES / "advisory-order-outage.md",
    "시세 지연 안내": EXAMPLES / "advisory-market-data-delay.md",
    "소수점 주문 안내": EXAMPLES / "advisory-fractional-order.md",
}

CASE_TYPES = {
    "투자 판단": "investment_decision",
    "주문장애": "order_outage",
    "시세 지연": "market_data_delay",
    "소수점 주문": "fractional_order",
}

STATUS_LABELS = {
    "inspected": "검사 완료",
    "awaiting_review": "검토 대기",
    "approved_with_findings": "예외 승인",
    "revising": "재검사",
    "rejected": "반려",
    "ready": "통과",
    "completed": "완료",
}

SEVERITY_LABELS = {
    "high": "높음",
    "medium": "보통",
    "low": "낮음",
    "info": "정보",
}


def reset_review() -> None:
    st.session_state.review_graph = build_review_graph()
    st.session_state.review_config = {
        "configurable": {"thread_id": f"ui-{uuid4()}"}
    }
    st.session_state.review_result = None


def run_review() -> None:
    reset_review()
    st.session_state.review_result = st.session_state.review_graph.invoke(
        {
            "draft": st.session_state.draft_input,
            "case_type": CASE_TYPES[st.session_state.case_type_label],
            "source": "streamlit-draft.md",
            "revision_count": 0,
            "audit_events": [],
        },
        config=st.session_state.review_config,
    )


def resume_review(decision: str) -> None:
    response = {
        "decision": decision,
        "note": st.session_state.reviewer_note,
    }
    if decision == "edit":
        edited_draft = st.session_state.edited_draft.strip()
        if not edited_draft:
            st.error("수정 후 재검사하려면 수정본을 입력해야 합니다.")
            return
        response["edited_draft"] = edited_draft

    st.session_state.review_result = st.session_state.review_graph.invoke(
        Command(resume=response),
        config=st.session_state.review_config,
    )
    st.session_state.pending_draft_input = st.session_state.review_result.get(
        "draft",
        st.session_state.draft_input,
    )
    st.rerun()


st.set_page_config(
    page_title="Investment Answer Review Workflow",
    page_icon="✓",
    layout="wide",
)

if "selected_example" not in st.session_state:
    st.session_state.selected_example = next(iter(EXAMPLE_OPTIONS))
if "case_type_label" not in st.session_state:
    st.session_state.case_type_label = next(iter(CASE_TYPES))
if "draft_input" not in st.session_state:
    st.session_state.draft_input = EXAMPLE_OPTIONS[
        st.session_state.selected_example
    ].read_text(encoding="utf-8")
if "pending_draft_input" in st.session_state:
    st.session_state.draft_input = st.session_state.pop("pending_draft_input")
if "review_graph" not in st.session_state:
    reset_review()

st.title("Investment Answer Review Workflow")
st.caption(
    "공개 근거 기반 품질 검사를 실행하고, 위험 항목은 사람의 승인·수정·반려를 기다립니다."
)

with st.sidebar:
    st.subheader("검사 설정")
    selected_example = st.selectbox(
        "예제",
        EXAMPLE_OPTIONS,
        key="selected_example",
    )
    st.selectbox("답변 유형", CASE_TYPES, key="case_type_label")
    if st.button("예제 불러오기", use_container_width=True):
        st.session_state.draft_input = EXAMPLE_OPTIONS[selected_example].read_text(
            encoding="utf-8"
        )
        reset_review()
        st.rerun()

st.text_area(
    "검토할 답변 초안",
    key="draft_input",
    height=360,
)
st.button(
    "검사 시작",
    type="primary",
    on_click=run_review,
    use_container_width=True,
)

result = st.session_state.review_result
if result:
    st.divider()
    findings = result.get("findings", [])
    status_columns = st.columns(4)
    status = result.get("status", "-")
    status_columns[0].metric("상태", STATUS_LABELS.get(status, status))
    status_columns[1].metric("Finding", len(findings))
    max_severity = result.get("max_severity")
    status_columns[2].metric(
        "최고 위험도",
        SEVERITY_LABELS.get(max_severity, max_severity or "없음"),
    )
    status_columns[3].metric("수정 횟수", result.get("revision_count", 0))

    if findings:
        st.subheader("검수 결과")
        st.dataframe(
            [
                {
                    "위험도": SEVERITY_LABELS.get(
                        finding["severity"],
                        finding["severity"],
                    ),
                    "분류": finding["category"],
                    "설명": finding["message"],
                    "수정 제안": finding["suggestion"],
                    "공개 근거": finding["evidence_url"],
                }
                for finding in findings
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("현재 검사 기준에서 추가 검토 항목이 없습니다.")

    pending = get_interrupt_payload(result)
    if pending:
        st.subheader("사람 검토")
        st.info(
            "자동 검사는 최종 판단을 대신하지 않습니다. 검수 결과를 확인하고 다음 동작을 선택하세요."
        )
        st.text_input("검토 메모", key="reviewer_note")
        st.text_area(
            "수정본",
            value=result.get("draft", st.session_state.draft_input),
            key="edited_draft",
            height=260,
        )
        action_columns = st.columns(3)
        if action_columns[0].button("승인", use_container_width=True):
            resume_review("approve")
        if action_columns[1].button(
            "수정 후 재검사",
            type="primary",
            use_container_width=True,
        ):
            resume_review("edit")
        if action_columns[2].button("반려", use_container_width=True):
            resume_review("reject")
    else:
        outcome = result.get("outcome")
        if outcome == "ready":
            st.success("검사가 완료되어 다음 단계로 진행할 수 있습니다.")
        elif outcome == "approved_with_findings":
            st.warning("검토 항목이 남아 있는 상태로 사람이 승인했습니다.")
        elif outcome == "rejected":
            st.error("검수자가 답변 초안을 반려했습니다.")

    st.subheader("감사 기록")
    st.dataframe(
        result.get("audit_events", []),
        use_container_width=True,
        hide_index=True,
    )
    audit_payload = {
        "status": result.get("status"),
        "outcome": result.get("outcome"),
        "decision": result.get("decision"),
        "reviewer_note": result.get("reviewer_note", ""),
        "revision_count": result.get("revision_count", 0),
        "findings": findings,
        "audit_events": result.get("audit_events", []),
    }
    st.download_button(
        "감사 기록 JSON 다운로드",
        data=json.dumps(audit_payload, ensure_ascii=False, indent=2),
        file_name="investment-answer-review-audit.json",
        mime="application/json",
    )
