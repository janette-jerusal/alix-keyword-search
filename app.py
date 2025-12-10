import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="User Story Keyword Filter", layout="wide")

st.title("Alix Keyword Tracer")

st.markdown("""
Upload one or more Excel files containing user stories.  
Then filter by keywords and choose **which columns** to keep in the output.
""")


# -----------------------------------
# Helper for detecting columns
# -----------------------------------
def detect_column(columns, candidates):
    cols_lower = [c.lower() for c in columns]
    for c in candidates:
        if c in cols_lower:
            return columns[cols_lower.index(c)]
    return None


# -----------------------------------
# Upload files
# -----------------------------------
uploaded_files = st.file_uploader(
    "Upload one or more Excel files",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
)

if uploaded_files:
    dfs = []

    st.subheader("Step 1: Select Sheet for Each File")

    for file in uploaded_files:
        try:
            excel_obj = pd.ExcelFile(file)
            sheet_name = st.selectbox(
                f"Choose a sheet from **{file.name}**:",
                excel_obj.sheet_names,
                key=file.name
            )
            df = pd.read_excel(excel_obj, sheet_name=sheet_name)
            dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    if not dfs:
        st.stop()

    combined_df = pd.concat(dfs, ignore_index=True)

    # -----------------------------
    # Step 2: Column Mapping
    # -----------------------------
    st.subheader("Step 2: Choose Columns for Keyword Filtering")

    columns = list(combined_df.columns)

    # These two define WHERE we search for keywords
    id_col = st.selectbox(
        "Select the **User Story ID** column (used for identification)",
        options=columns,
        index=columns.index(detect_column(columns, ["user story id", "id", "story id"]))
        if detect_column(columns, ["user story id", "id", "story id"]) else 0
    )

    desc_col = st.selectbox(
        "Select the **User Story Description** column (searched for keywords)",
        options=columns,
        index=columns.index(detect_column(columns, ["description", "user story description", "desc"]))
        if detect_column(columns, ["description", "user story description", "desc"]) else 1
    )

    # -----------------------------
    # NEW: User chooses which columns to retain
    # -----------------------------
    st.subheader("Step 3: Choose Which Columns to Retain in Output")

    retain_cols = st.multiselect(
        "Select columns to KEEP in the results:",
        options=columns,
        default=[id_col, desc_col]  # By default keep ID + Description
    )

    if len(retain_cols) == 0:
        st.warning("Please select at least one column to retain.")
        st.stop()

    st.write("Preview of selected columns:")
    st.dataframe(
        combined_df[retain_cols].head(10),
        use_container_width=True
    )

    # -----------------------------
    # Step 4: Keyword Filtering
    # -----------------------------
    st.subheader("Step 4: Enter Keywords")

    keyword_text = st.text_input(
        "Keywords (comma-separated):",
        value="security, masking, privacy"
    )

    match_mode = st.radio(
        "Match mode",
        ["Any keyword (OR)", "All keywords (AND)"],
        horizontal=True,
    )

    # -----------------------------
    # Run filtering
    # -----------------------------
    if st.button("Filter Stories"):
        if not keyword_text.strip():
            st.warning("Please enter at least one keyword.")
            st.stop()

        keywords = [k.strip() for k in keyword_text.split(",") if k.strip()]
        if not keywords:
            st.warning("No valid keywords parsed.")
            st.stop()

        descriptions = combined_df[desc_col].astype(str)

        if match_mode == "Any keyword (OR)":
            pattern = "|".join(re.escape(k) for k in keywords)
            mask = descriptions.str.contains(pattern, case=False, na=False)
        else:
            mask = pd.Series(True, index=combined_df.index)
            for k in keywords:
                mask &= descriptions.str.contains(re.escape(k), case=False, na=False)

        filtered = combined_df.loc[mask, retain_cols].copy()

        st.subheader(f"Results ({len(filtered)} stories found)")
        st.dataframe(filtered, use_container_width=True)

        # -----------------------------
        # Excel export
        # -----------------------------
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            filtered.to_excel(writer, index=False, sheet_name="FilteredStories")
        output.seek(0)

        st.download_button(
            label="💾 Download Results as Excel",
            data=output,
            file_name="filtered_user_stories.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


else:
    st.info("Upload one or more Excel files to begin.")

