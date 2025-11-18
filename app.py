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

# Small CSS touch to get a bit closer to your Figma vibe
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
        # nothing selected -> show everything (or nothing; I choose everything)
        return df


# -----------------------------------------------------------------------------
# TOP NAVBAR
# -----------------------------------------------------------------------------
screen_titles = {
    1: "Variable Mapping Setup",
    2: "Select Data Source",
    3: "Choose Variables",
    4: "Show & Export Selected Variables",
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

# Back/Next buttons in the navbar right side
nav_cols = st.columns([8, 2, 2])
with nav_cols[1]:
    if st.session_state.step > 1:
        if st.button("◀ Back", use_container_width=True):
            go_back()
with nav_cols[2]:
    # We will enable/disable inside each step (here button is just a placeholder)
    pass

st.write("")  # small spacer

# -----------------------------------------------------------------------------
# STEP 1 – Setup
# -----------------------------------------------------------------------------
if st.session_state.step == 1:
    st.markdown('<div class="step-title">Variable Mapping Setup</div>', unsafe_allow_html=True)
    st.write(
        "Welcome! Choose whether you want to start a new mapping or load an existing CSV configuration."
    )

    project_type = st.radio(
        "Project type",
        ["New project", "Load existing configuration"],
        index=0 if st.session_state.project_type == "New project" else 1,
    )
    st.session_state.project_type = project_type

    uploaded_file = None
    if project_type == "Load existing configuration":
        st.markdown("#### Upload configuration CSV")
        uploaded_file = st.file_uploader(
            "Select a CSV file previously exported from this tool.",
            type=["csv"],
        )

        if uploaded_file is not None:
            try:
                # Very simple CSV reader; assumes a header row
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
    if project_type == "Load existing configuration" and st.session_state.imported_config is None:
        can_next = False

    if st.button("Next ▶", disabled=not can_next):
        # Optional: pre-select variables based on imported config by name
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
    st.markdown('<div class="step-title">Select Data Source</div>', unsafe_allow_html=True)
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

    st.info("You can select one or both. This will filter which variables appear in the next step.")

    st.write("---")
    can_next = epic_checked or pdms_checked
    if st.button("Next ▶", disabled=not can_next):
        go_next()

# -----------------------------------------------------------------------------
# STEP 3 – Choose Variables
# -----------------------------------------------------------------------------
elif st.session_state.step == 3:
    st.markdown('<div class="step-title">Choose Variables</div>', unsafe_allow_html=True)

    # Filters
    filt_col1, filt_col2 = st.columns([2, 3])
    with filt_col1:
        organ_system_filter = st.selectbox(
            "Organ system filter",
            ["All systems", "Cardiology", "Respiratory", "Neurology"],
            index=0,
        )
    with filt_col2:
        search_query = st.text_input("Search variables")

    df = filter_catalogue_by_sources()

    if organ_system_filter != "All systems":
        df = df[df["organ_system"] == organ_system_filter]

    if search_query.strip():
        q = search_query.strip().lower()
        df = df[df["name"].str.lower().str.contains(q)]

    # Map option labels to IDs
    def make_label(row):
        src_parts = []
        if row["epic_id"]:
            src_parts.append("EPIC")
        if row["pdms_id"]:
            src_parts.append("PDMS")
        src = "/".join(src_parts) if src_parts else "–"
        return f"{row['organ_system']} · {row['group']} · {row['name']} [{src}]"

    df = df.copy()
    df["label"] = df.apply(make_label, axis=1)

    id_to_label = dict(zip(df["id"], df["label"]))
    label_to_id = {v: k for k, v in id_to_label.items()}

    # figure out which labels are currently selected
    current_ids = st.session_state.selected_variable_ids
    current_labels = [id_to_label[i] for i in current_ids if i in id_to_label]

    selected_labels = st.multiselect(
        "Available variables",
        options=df["label"].tolist(),
        default=current_labels,
        help="Select variables to include in your mapping.",
    )

    # update session_state
    new_ids = {label_to_id[lbl] for lbl in selected_labels}
    st.session_state.selected_variable_ids = new_ids

    st.write("### Selected variables preview")
    if new_ids:
        selected_df = CATALOGUE_DF[CATALOGUE_DF["id"].isin(new_ids)].copy()
        st.dataframe(
            selected_df[
                ["name", "epic_id", "pdms_id", "organ_system", "group", "unit"]
            ],
            use_container_width=True,
        )
    else:
        st.info("No variables selected yet.")

    st.write("---")
    can_next = len(new_ids) > 0
    if st.button("Next ▶", disabled=not can_next):
        # Build export table (initial) from catalogue
        rows = []
        for vid in new_ids:
            row = CATALOGUE_DF[CATALOGUE_DF["id"] == vid].iloc[0]
            # Determine source string
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
# STEP 4 – Show & Export Selected Variables
# -----------------------------------------------------------------------------
elif st.session_state.step == 4:
    st.markdown(
        '<div class="step-title">Show & Export Selected Variables</div>',
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
                ["bpm", "mmHg", "L/min", "%", "breaths/min", "score", "mg/dL", "°C", "custom"],
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
            st.session_state.export_table = df[~df["Variable"].isin(to_delete)].reset_index(drop=True)
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
