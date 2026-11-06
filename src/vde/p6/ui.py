"""Explicit Order submission and passive, immutable-byte delivery controls."""
from dataclasses import asdict
import mimetypes
import sys
from uuid import uuid4

import streamlit as st
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx

from vde.errors import StorageError
from vde.persistence.uow import UnitOfWork
from vde.recovery import recover

from .delivery import DeliveryService, P6Error
from .orders import CreateOrderService


_FORM_FIELDS = ("p6_order_title", "p6_order_listing_text", "p6_order_listing_url",
                "p6_order_budget", "p6_order_deadline", "p6_order_notes")
_SNAPSHOT = "p6_delivery_snapshot"
_SELECTION = "p6_delivery_selection"
_CONTEXT = "p6_delivery_context_key"


def _clear_snapshot():
    st.session_state.pop(_SNAPSHOT, None)
    st.session_state.pop(_CONTEXT, None)


def _fresh_health(env):
    if env.workspace is None:
        raise StorageError("Workspace unavailable")
    return recover(env.database, env.workspace)


def _health_message(report):
    st.warning(f"Current local storage health: {report.health}. Create and download require ready storage.")
    if report.errors:
        for error in report.errors:
            st.json(error)
    if report.staging or report.orphans or report.stale_runs:
        st.json({"staging": report.staging, "orphans": report.orphans,
                 "stale_runs": report.stale_runs})


def _show_error(exc):
    st.error(exc.code if isinstance(exc, P6Error) else "STORAGE_ERROR")
    st.json(exc.public())


def _reset_form():
    for key in _FORM_FIELDS:
        st.session_state.pop(key, None)
    st.session_state["p6_order_request_token"] = str(uuid4())


def order_panel(env):
    st.subheader("Create Order")
    st.caption("Submit creates a DRAFT Order. Review, publish and approve Brief and Spec separately in the manual workflow below. Only outer title spaces are trimmed; listing text is stored verbatim.")
    if st.session_state.pop("p6_order_reset_pending", False):
        _reset_form()
    if "p6_order_request_token" not in st.session_state:
        st.session_state["p6_order_request_token"] = str(uuid4())
    if st.button("New Order form", key="p6_new_order"):
        _reset_form()
    notice = st.session_state.pop("p6_order_created_notice", None)
    if notice:
        st.success(f"DRAFT Order created: {notice}")
    try:
        health = _fresh_health(env)
        ready = health.health == "ready"
        if not ready:
            _health_message(health)
        with st.form("p6_order_form"):
            title = st.text_input("Order title", key="p6_order_title", disabled=not ready)
            listing_text = st.text_area("Listing text", key="p6_order_listing_text", disabled=not ready)
            listing_url = st.text_input("Listing URL (optional)", key="p6_order_listing_url", disabled=not ready)
            budget = st.text_input("Budget (canonical decimal, optional)", key="p6_order_budget", disabled=not ready)
            deadline = st.text_input("Deadline (UTC YYYY-MM-DDTHH:MM:SSZ, optional)", key="p6_order_deadline", disabled=not ready)
            notes = st.text_area("Notes (optional)", key="p6_order_notes", disabled=not ready)
            submitted = st.form_submit_button("Create DRAFT Order", disabled=not ready)
        if submitted:
            record = CreateOrderService(env).create(
                st.session_state["p6_order_request_token"], title=title,
                listing_text=listing_text, listing_url=listing_url or None,
                budget=budget or None, deadline=deadline or None, notes=notes or None)
            st.session_state["p6_last_order_id"] = record.id
            st.session_state["p6_order_created_notice"] = record.id
            st.session_state["p6_order_reset_pending"] = True
            # Rotate only after success. Failed submissions retain their exact
            # token and form fields; passive rerenders never invoke create().
            st.rerun()
    except (P6Error, StorageError) as exc:
        _show_error(exc)


def _display_view(view):
    report = view.report
    if view.diagnostic:
        st.error("NEEDS_FIX — diagnostic result — NOT FOR DELIVERY")
    else:
        st.success(f"READY — {report['overall_status']}")
    st.json({"order_id": view.order.id, "run_id": view.run.id,
             "order_status": view.order.status, "run_status": view.run.status,
             "brief_version_id": view.brief.id, "brief_content_hash": view.brief.content_hash,
             "transformation_spec_version_id": view.spec.id,
             "transformation_spec_content_hash": view.spec.content_hash,
             "approvals": [asdict(item) for item in view.approvals],
             "qa_overall_status": report["overall_status"],
             "warnings": report["warnings"], "blocker_count": len(report["blocking_issues"]),
             "row_count": report["dataset_summary"]["row_count"],
             "column_count": report["dataset_summary"]["column_count"],
             "artifact_type": view.artifact.artifact_type, "format": view.artifact.format,
             "checksum": view.artifact.checksum,
             "file_size_bytes": report["dataset_summary"]["file_size_bytes"]})


def _download_buttons(snapshot):
    """Publish both widget URLs only after their shared RSS guard succeeds.

    Streamlit 1.50 registers downloadable media before enqueueing a widget.
    Buffer this context's two widget messages and revoke only newly allocated
    media if binding fails; ordinary orphan cleanup deliberately retains it.
    These private compatibility points are covered by the P6 HTTP fault probe.
    """
    context = get_script_run_ctx()
    if context is None or not runtime.exists():
        raise P6Error("STORAGE_ERROR", "Verified download requires an active Streamlit session.")
    manager = runtime.get_instance().media_file_mgr
    enqueue = context._enqueue
    with manager._lock:
        previous_ids = set(manager._file_metadata)
        previous_coordinates = dict(manager._files_by_session_and_coord.get(context.session_id, {}))
    # Streamlit 1.50 derives the URL extension from this standard registry;
    # Tornado derives the response Content-Type from the same extension. Keep
    # the exact C04 UTF-8 MIME at both boundaries rather than only in a widget.
    mimetypes.add_type("application/json; charset=utf-8", ".vde-qa-json")
    pending = []
    published = False
    context._enqueue = pending.append
    try:
        with snapshot.guard.binding():
            st.download_button(
                "Download diagnostic — NOT FOR DELIVERY" if snapshot.view.diagnostic else "Download verified result",
                data=snapshot.result_bytes, file_name=snapshot.result_name,
                mime=snapshot.result_mime, key="p6_download_result")
            st.download_button("Download QAReport", data=snapshot.report_bytes,
                               file_name=snapshot.report_name, mime=snapshot.report_mime,
                               key="p6_download_report")
        # No payload URL reaches the browser before both buffers have passed
        # the sampled post-binding check against the preparation baseline.
        for message in pending:
            enqueue(message)
        published = True
    finally:
        context._enqueue = enqueue
        if not published:
            with manager._lock:
                current = manager._files_by_session_and_coord.get(context.session_id, {})
                allocated = set(current.values()) - previous_ids
                manager._files_by_session_and_coord[context.session_id] = previous_coordinates
                for file_id in allocated:
                    if file_id in manager._file_metadata:
                        manager._delete_file(file_id)
        pending.clear()


def delivery_panel(env):
    st.subheader("Verified result and QAReport downloads")
    st.caption("Choose an Order and Run, then prepare a verified copy. Preparation reads and verifies persisted data; the download transfers those immutable bytes. Disk is not rechecked at the final browser click. External delivery is manual.")
    binding_started = False
    notice = st.session_state.pop("p6_delivery_error_notice", None)
    if notice:
        st.error(notice["code"])
        st.json(notice)
    try:
        health = _fresh_health(env)
        if health.health != "ready":
            _clear_snapshot()
            _health_message(health)
            return
        with UnitOfWork(env.database, env.workspace) as uow:
            orders = uow.orders.list()
        if not orders:
            _clear_snapshot()
            st.info("Create an Order and complete the manual workflow to prepare downloads.")
            return
        order_id = st.selectbox("Download Order", [order.id for order in orders],
                                index=None, key="p6_delivery_order")
        selection = (str(env.database), order_id, None)
        if order_id is None:
            _clear_snapshot()
            st.session_state[_SELECTION] = selection
            return
        with UnitOfWork(env.database, env.workspace) as uow:
            runs = uow.runs.list_for_order(order_id)
        if not runs:
            _clear_snapshot()
            st.session_state[_SELECTION] = selection
            st.info("No Run exists for this Order. Continue using the explicit manual panels.")
            return
        run_id = st.selectbox("Download Run", [run.id for run in runs],
                              index=None, key="p6_delivery_run")
        selection = (str(env.database), order_id, run_id)
        if st.session_state.get(_SELECTION) != selection:
            _clear_snapshot()
        st.session_state[_SELECTION] = selection
        if run_id is None:
            return
        service = DeliveryService(env)
        # Always repeat the complete read-only decision, even with a prepared
        # copy. A session key is never authority to expose bytes.
        view = service.view(order_id, run_id)
        snapshot = st.session_state.get(_SNAPSHOT)
        if snapshot is not None and (snapshot.context_key != view.context_key or
                                     st.session_state.get(_CONTEXT) != view.context_key):
            _clear_snapshot()
            snapshot = None
        _display_view(view)
        if st.button("Prepare verified download", key="p6_prepare_download"):
            _clear_snapshot()
            snapshot = None
            candidate = service.prepare(order_id, run_id)
            # Guard against a selection change while the verified bytes were
            # prepared; the service also rechecks its persisted context.
            if st.session_state.get(_SELECTION) != selection:
                raise P6Error("P6_NOT_READY", "Selection changed while preparing the download.")
            st.session_state[_SNAPSHOT] = candidate
            st.session_state[_CONTEXT] = candidate.context_key
            snapshot = candidate
        if snapshot is not None:
            binding_started = True
            _download_buttons(snapshot)
            st.json({"download_resources": snapshot.resources})
    except (P6Error, StorageError) as exc:
        _clear_snapshot()
        if binding_started:
            # Start a passive render after revoking the failed binding so no
            # stale widget registration survives in the current session.
            st.session_state["p6_delivery_error_notice"] = exc.public()
            st.rerun()
        _show_error(exc)
    finally:
        # Unexpected errors still propagate for debugging and cannot leave an
        # authorized session buffer behind.
        if sys.exc_info()[0] is not None:
            _clear_snapshot()
