import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

# -----------------------------------------------------------------------------
# Basic configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Variable Mapping Tool",
    layout="wide",
)

# Small CSS touch to get closer to your Figma vibe
st.markdown(
    """
    <style>
    .top-bar {
        background-color: #ffffff;
        border-bottom: 1px solid #e5e7eb;
        padding: 0.75rem 2rem;
        margin: -1rem -1rem 1rem -1rem;
    }
    .top-bar-title {
        font-weight: 600;
        color: #111827;
        font-size: 1rem;
    }
    .top-bar-sub {
        color: #4b5563;
        font-size: 0.9rem;
        margin-left: 0.25rem;
    }
    .step-title {
        font-weight: 600;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }
    /* Panel styling */
    .stApp {
        background-color: #f9fafb;
    }
    .mapping-panel {
        background-color: #ffffff;
        padding: 1rem 1.25rem;
        border-radius: 0.75rem;
        border: 1px solid #e5e7eb;
    }
    .side-panel-title {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }
    .side-panel-subtitle {
        font-size: 0.85rem;
        color: #6b7280;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Mock variable catalogue (similar to your treeData in React)
# -----------------------------------------------------------------------------
VARIABLES_CATALOGUE = [
    # Cardiology / Heart
    dict(
        id="hr-001",
        name="Heart Rate",
        organ_system="Cardiology",
        group="Heart",
        epic_id="E-HR-001",
        pdms_id="P-HR-001",
        unit="bpm",
    ),
    dict(
        id="bp-001",
        name="Blood Pressure",
        organ_system="Cardiology",
        group="Heart",
        epic_id="E-BP-001",
        pdms_id="P-BP-001",
        unit="mmHg",
    ),
    dict(
        id="co-001",
        name="Cardiac Output",
        organ_system="Cardiology",
        group="Heart",
        epic_id="E-CO-001",
        pdms_id="P-CO-001",
        unit="L/min",
    ),
    dict(
        id="qt-001",
        name="QT Interval",
        organ_system="Cardiology",
        group="ECG",
        epic_id="E-QT-001",
        pdms_id="P-QT-001",
        unit="ms",
    ),
    # Respiratory / Lungs
    dict(
        id="spo2-001",
        name="SpO2",
        organ_system="Respiratory",
        group="Lungs",
        epic_id="E-SPO2-001",
        pdms_id="P-SPO2-001",
        unit="%",
    ),
    dict(
        id="rr-001",
        name="Respiratory Rate",
        organ_system="Respiratory",
        group="Lungs",
        epic_id="E-RR-001",
        pdms_id="P-RR-001",
        unit="breaths/min",
    ),
    # Neurology
    dict(
        id="gcs-001",
        name="Glasgow Coma Scale",
        organ_system="Neurology",
        group="Brain",
        epic_id="E-GCS-001",
        pdms_id="P-GCS-001",
        unit="score",
    ),
    dict(
        id="mf-epic-001",
        name="Motor Function (EPIC only)",
        organ_system="Neurology",
        group="Motor",
        epic_id="E-MF-001",
        pdms_id="",
        unit="score",
    ),
    dict(
        id="mf-pdms-001",
        name="Motor Function (PDMS only)",
        organ_system="Neurology",
        group="Motor",
        epic_id="",
        pdms_id="P-MF-001",
        unit="score",
    ),
]

CATALOGUE_DF = pd.DataFrame(VARIABLES_CATALOGUE)

# -----------------------------------------------------------------------------
# Session-state helpers
# -----------------------------------------------------------------------------
def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "project_type" not in st.session_state:
        st.session_state.project_type = "New project"
    if "imported_config" not in st.session_state:
        st.session_state.imported_config = None  # DataFrame
    if "selected_sources" not in st.session_state:
        st.session_state.selected_sources = {"EPIC": False, "PDMS": False}
    if "selected_variable_ids" not in st.session_state:
        st.session_state.selected_variable_ids = set()
    if "export_table" not in st.session_state:
        st.session_state.export_table = pd.DataFrame(
            columns=[
                "Variable",
                "Source",
                "ID",
                "Unit",
                "Organ System",
                "Group",
                "Status",
            ]
        )

init_state()


def go_next():
    st.session_state.step = min(st.session_state.step + 1, 4)


def go_back():
    st.session_state.step = max(st.session_state.step - 1, 1)


# -----------------------------------------------------------------------------
# Helper: Filter catalogue by selected sources (EPIC / PDMS)
# -----------------------------------------------------------------------------
def filter_catalogue_by_sources():
    df = CATALOGUE_DF.copy()
    epic = st.session_state.selected_sources["EPIC"]
    pdms = st.session_state.selected_sources["PDMS"]

    if epic and pdms:
        # keep rows that have at least one ID
        return df[(df["epic_id"] != "") | (df["pdms_id"] != "")]
    elif epic and not pdms:
        return df[df["epic_id"] != ""]
    elif pdms and not epic:
        return df[df["pdms_id"] != ""]
    else:
        # nothing selected -> show everything
        return df


# -----------------------------------------------------------------------------
# TOP NAVBAR
# -----------------------------------------------------------------------------
screen_titles = {
    1: "Variable Mapping Setup",
    2: "Select Data Source",
    3: "Map Variables",
    4: "Review & Export",
}

st.markdown(
    f"""
    <div class="top-bar">
        <span class="top-bar-title">Variable Mapping Tool</span>
        <span class="top-bar-sub">• {screen_titles[st.session_state.step]}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Back button in the navbar right side
nav_cols = st.columns([8, 2, 2])
with nav_cols[1]:
    if st.session_state.step > 1:
        if st.button("◀ Back", use_container_width=True, key="back_button"):
            go_back()
with nav_cols[2]:
    # real "Next" buttons are inside each step, so nothing here
    pass

st.write("")  # small spacer

# -----------------------------------------------------------------------------
# STEP 1 – Setup
# -----------------------------------------------------------------------------
if st.session_state.step == 1:
    st.markdown(
        '<div class="step-title">Variable Mapping Setup</div>',
        unsafe_allow_html=True,
    )
    st.write(
        "Welcome! Choose whether you want to start a new mapping or load an existing CSV configuration."
    )

    project_type = st.radio(
        "Project type",
        ["New project", "Load existing configuration"],
        index=0 if st.session_state.project_type == "New project" else 1,
    )
    st.session_state.project_type = project_type

    if project_type == "Load existing configuration":
        st.markdown("#### Upload configuration CSV")
        uploaded_file = st.file_uploader(
            "Select a CSV file previously exported from this tool.",
            type=["csv"],
        )

        if uploaded_file is not None:
            try:
                config_df = pd.read_csv(uploaded_file)
                st.session_state.imported_config = config_df
                st.success(f"Loaded {len(config_df)} rows from `{uploaded_file.name}`.")
                st.dataframe(config_df.head(), use_container_width=True)
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
        else:
            st.info("Upload a CSV file to proceed.")

    st.write("---")
    can_next = True
    if (
        project_type == "Load existing configuration"
        and st.session_state.imported_config is None
    ):
        can_next = False

    if st.button("Next ▶", key="next_step1", disabled=not can_next):
        # If config loaded, pre-select variables by name
        if st.session_state.imported_config is not None:
            imported_names = {
                str(v).strip().lower()
                for v in st.session_state.imported_config["Variable"].tolist()
            }
            preselected_ids = CATALOGUE_DF[
                CATALOGUE_DF["name"].str.lower().isin(imported_names)
            ]["id"].tolist()
            st.session_state.selected_variable_ids = set(preselected_ids)

        go_next()

# -----------------------------------------------------------------------------
# STEP 2 – Data Source Selection
# -----------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.markdown(
        '<div class="step-title">Select Data Source</div>',
        unsafe_allow_html=True,
    )
    st.write("Choose which data sources you want to include in your mapping.")

    col1, col2 = st.columns(2)
    with col1:
        epic_checked = st.checkbox(
            "EPIC",
            value=st.session_state.selected_sources["EPIC"],
        )
    with col2:
        pdms_checked = st.checkbox(
            "PDMS",
            value=st.session_state.selected_sources["PDMS"],
        )
    st.session_state.selected_sources = {
        "EPIC": epic_checked,
        "PDMS": pdms_checked,
    }

    st.info(
        "You can select one or both. This will filter which variables appear in the mapping step."
    )

    st.write("---")
    can_next = epic_checked or pdms_checked
    if st.button("Next ▶", key="next_step2", disabled=not can_next):
        go_next()

# -----------------------------------------------------------------------------
# STEP 3 – Map Variables (tree-like structure)
# -----------------------------------------------------------------------------
elif st.session_state.step == 3:
    st.markdown(
        '<div class="step-title">Map Variables</div>',
        unsafe_allow_html=True,
    )

    df = filter_catalogue_by_sources()

    left_col, right_col = st.columns([2.2, 3])

    # LEFT: "Tree" of organ system -> group -> variables with checkboxes
    with left_col:
        st.markdown('<div class="mapping-panel">', unsafe_allow_html=True)
        st.markdown(
            '<div class="side-panel-title">Variable catalogue</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="side-panel-subtitle">Browse by organ system & group. Tick variables to add them to your mapping.</div>',
            unsafe_allow_html=True,
        )

        organ_systems = sorted(df["organ_system"].unique())

        for os in organ_systems:
            with st.expander(os, expanded=True):
                os_df = df[df["organ_system"] == os]
                groups = sorted(os_df["group"].unique())
                for grp in groups:
                    st.markdown(f"**{grp}**")
                    grp_df = os_df[os_df["group"] == grp]

                    for _, row in grp_df.iterrows():
                        src_parts = []
                        if row["epic_id"]:
                            src_parts.append("EPIC")
                        if row["pdms_id"]:
                            src_parts.append("PDMS")
                        src_label = "/".join(src_parts) if src_parts else "–"

                        key = f"var_{row['id']}"
                        default_checked = row["id"] in st.session_state.selected_variable_ids
                        st.checkbox(
                            f"{row['name']}  ·  {row['unit']}  [{src_label}]",
                            value=default_checked,
                            key=key,
                        )
                    st.write("")  # small space between groups

        st.markdown('</div>', unsafe_allow_html=True)

    # After rendering all checkboxes, recompute selected IDs from their states
    selected_ids = {
        row["id"]
        for _, row in df.iterrows()
        if st.session_state.get(f"var_{row['id']}", False)
    }
    st.session_state.selected_variable_ids = selected_ids

    # RIGHT: Selected variables preview
    with right_col:
        st.markdown('<div class="mapping-panel">', unsafe_allow_html=True)
        st.markdown("#### Selected variables", unsafe_allow_html=True)

        if selected_ids:
            selected_df = CATALOGUE_DF[CATALOGUE_DF["id"].isin(selected_ids)].copy()
            selected_df_display = selected_df[
                ["name", "epic_id", "pdms_id", "organ_system", "group", "unit"]
            ].rename(
                columns={
                    "name": "Variable",
                    "epic_id": "EPIC ID",
                    "pdms_id": "PDMS ID",
                    "organ_system": "Organ system",
                    "group": "Group",
                    "unit": "Unit",
                }
            )
            st.dataframe(selected_df_display, use_container_width=True, height=420)
            st.caption(f"{len(selected_ids)} variable(s) selected.")
        else:
            st.info("Tick variables on the left to include them in your mapping.")

        st.markdown('</div>', unsafe_allow_html=True)

    st.write("---")
    can_next = len(selected_ids) > 0
    if st.button("Next ▶", key="next_step3", disabled=not can_next):
        # Build export table (initial) from catalogue
        rows = []
        for vid in selected_ids:
            row = CATALOGUE_DF[CATALOGUE_DF["id"] == vid].iloc[0]
            has_epic = bool(row["epic_id"])
            has_pdms = bool(row["pdms_id"])

            if has_epic and has_pdms:
                source = "Both"
                id_code = f"{row['epic_id']} / {row['pdms_id']}"
            elif has_epic:
                source = "EPIC"
                id_code = row["epic_id"]
            elif has_pdms:
                source = "PDMS"
                id_code = row["pdms_id"]
            else:
                source = "-"
                id_code = "-"

            rows.append(
                dict(
                    Variable=row["name"],
                    Source=source,
                    ID=id_code,
                    Unit=row["unit"],
                    Organ_System=row["organ_system"],
                    Group=row["group"],
                    Status="Published",
                )
            )

        st.session_state.export_table = pd.DataFrame(rows)
        go_next()

# -----------------------------------------------------------------------------
# STEP 4 – Review & Export
# -----------------------------------------------------------------------------
elif st.session_state.step == 4:
    st.markdown(
        '<div class="step-title">Review & Export</div>',
        unsafe_allow_html=True,
    )

    df = st.session_state.export_table

    # ---- table display ----
    st.write("### Current variable mapping")
    if df.empty:
        st.warning("No variables to show – go back and select some.")
    else:
        st.dataframe(df, use_container_width=True)

    st.write("")

    # ---- add variable form ----
    st.write("### Add variable")
    with st.form("add_variable_form"):
        c1, c2, c3, c4 = st.columns([3, 1.5, 2, 1.5])
        with c1:
            var_name = st.text_input("Variable name")
        with c2:
            source = st.selectbox("Source", ["EPIC", "PDMS", "Both"])
        with c3:
            var_id = st.text_input("ID code (e.g. E-HR-001 / P-HR-001)")
        with c4:
            unit = st.selectbox(
                "Unit",
                [
                    "bpm",
                    "mmHg",
                    "L/min",
                    "%",
                    "breaths/min",
                    "score",
                    "mg/dL",
                    "°C",
                    "custom",
                ],
                index=0,
            )

        c5, c6 = st.columns(2)
        with c5:
            organ_system = st.text_input("Organ system", value="")
        with c6:
            group = st.text_input("Group", value="")

        submitted = st.form_submit_button("Add variable")
        if submitted:
            if not var_name or not var_id:
                st.warning("Please provide at least a variable name and an ID.")
            else:
                new_row = dict(
                    Variable=var_name,
                    Source=source,
                    ID=var_id,
                    Unit=unit,
                    Organ_System=organ_system or "General",
                    Group=group or "General",
                    Status="New",
                )
                st.session_state.export_table = pd.concat(
                    [st.session_state.export_table, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                st.success(f"Added variable '{var_name}'.")
                df = st.session_state.export_table  # refresh reference

    st.write("")

    # ---- delete variables ----
    if not df.empty:
        st.write("### Delete variables")
        to_delete = st.multiselect(
            "Select variables to delete",
            options=df["Variable"].tolist(),
        )
        if st.button("Delete selected", disabled=not to_delete):
            st.session_state.export_table = df[
                ~df["Variable"].isin(to_delete)
            ].reset_index(drop=True)
            st.success(f"Deleted {len(to_delete)} variable(s).")

    st.write("---")

    # ---- export CSV ----
    if not df.empty:
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        filename = f"variable-mapping-{datetime.now().date()}.csv"
        st.download_button(
            label="⬇️ Export CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
        )
    else:
        st.info("Nothing to export yet.")
