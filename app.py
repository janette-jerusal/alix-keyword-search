import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="User Story Keyword Filter", layout="wide")

st.title("🔎 User Story Keyword Filter")

st.markdown(
    """
Upload one or more Excel files containing user stories.  
Then filter by keywords (e.g., **security, masking, privacy**) to extract:

- **User Story ID**  
- **User Story Description**  
- **Topic Group**  
- **No**
"""
)

uploaded_files = st.file_uploader(
    "Upload one or more Excel files",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
)

# -------------------------
# Helper: auto-detect columns
# -------------------------
def autodetect(columns, targets):
    """Return first matching column from list of possible names."""
    cols_lower = [c.lower() for c in columns]
    for t in targets:
        if t in cols_lower:
            return columns[cols_lower.index(t)]
    return None


if uploaded_files:
    dfs = []
    for file in uploaded_files:
        try:
            df = pd.read_excel(file)
            dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    if not dfs:
        st.stop()

    combined_df = pd.concat(dfs, ignore_index=True)

    st.subheader("Step 1: Map your columns correctly")

    columns = list(combined_df.columns)

    id_col = st.selectbox(
        "User Story ID Column",
        options=columns,
        index=columns.index(autodetect(columns, ["user story id", "story id", "id"])) 
        if autodetect(columns, ["user story id", "story id", "id"]) else 0
    )

    desc_col = st.selectbox(
        "User Story Description Column",
        options=columns,
        index=columns.index(autodetect(columns, ["user story description", "description", "desc"])) 
        if autodetect(columns, ["user story description", "description", "desc"]) else 1
    )

    topic_col = st.selectbox(
        "Topic Group Column",
        options=columns,
        index=columns.index(autodetect(columns, ["topic group", "topic"])) 
        if autodetect(columns, ["topic group", "topic"]) else 2
    )

    no_col = st.selectbox(
        "No Column",
        options=columns,
        index=columns.index(autodetect(columns, ["no", "number", "num"])) 
        if autodetect(columns, ["no", "number", "num"]) else 3
    )

    st.write("Preview:")
    try:
        st.dataframe(
            combined_df[[id_col, desc_col, topic_col, no_col]].head(10),
            use_container_width=True
        )
    except:
        st.warning("Please make sure selected columns exist in all files.")

    st.subheader("Step 2: Enter keywords")

    keyword_text = st.text_input(
        "Keywords (comma-separated)",
        value="security, masking, privacy"
    )

    match_mode = st.radio(
        "Match mode",
        ["Any keyword (OR)", "All keywords (AND)"],
        horizontal=True,
    )

    if st.button("Filter Stories"):
        if not keyword_text.strip():
            st.warning("Please enter at least one keyword.")
            st.stop()

        keywords = [k.strip() for k in keyword_text.split(",") if k.strip()]
        if not keywords:
            st.warning("No valid keywords parsed.")
            st.stop()

        descriptions = combined_df[desc_col].astype(str)

        # Matching logic
        if match_mode == "Any keyword (OR)":
            pattern = "|".join(re.escape(k) for k in keywords)
            mask = descriptions.str.contains(pattern, case=False, na=False)
        else:
            mask = pd.Series(True, index=combined_df.index)
            for k in keywords:
                mask &= descriptions.str.contains(re.escape(k), case=False, na=False)

        # Extract exactly the 4 required columns
        filtered = combined_df.loc[
            mask, [id_col, desc_col, topic_col, no_col]
        ].copy()

        filtered.columns = [
            "User Story ID", "User Story Description", "Topic Group", "No"
        ]

        st.subheader(f"Results ({len(filtered)} stories found)")
        st.dataframe(filtered, use_container_width=True)

        # Excel export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            filtered.to_excel(writer, index=False, sheet_name="FilteredStories")
        output.seek(0)

        st.download_button(
            label="💾 Download Results as Excel",
            data=output,
            file_name="filtered_user_stories.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Upload one or more Excel files to begin.")
