import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------
# Setup: all operations happen inside one "workspace" folder
# so the app can never touch files outside it.
# ---------------------------------------------------------------
st.set_page_config(page_title="File & Folder Manager", page_icon="🗂️", layout="wide")

BASE = Path("workspace")
BASE.mkdir(exist_ok=True)
BASE_RESOLVED = BASE.resolve()


def safe_path(name: str) -> Path:
    """Return a path inside BASE, or raise ValueError if it tries to escape."""
    name = name.strip()
    if not name:
        raise ValueError("Name cannot be empty.")
    p = (BASE / name).resolve()
    if p != BASE_RESOLVED and BASE_RESOLVED not in p.parents:
        raise ValueError("Path must stay inside the workspace folder.")
    return p


def list_items():
    return sorted(BASE.rglob("*"))


def list_folders():
    return [str(p.relative_to(BASE)) for p in list_items() if p.is_dir()]


def list_files():
    return [str(p.relative_to(BASE)) for p in list_items() if p.is_file()]


# ---------------------------------------------------------------
# Folder operations
# ---------------------------------------------------------------
def ui_create_folder():
    st.subheader("📁 Create a folder")
    with st.form("create_folder_form", clear_on_submit=True):
        name = st.text_input("Folder name (you can use nested paths like `a/b`)")
        submitted = st.form_submit_button("Create folder", type="primary")
    if submitted:
        try:
            p = safe_path(name)
            if p.exists():
                st.error("Folder already exists. Try another name.")
            else:
                p.mkdir(parents=True)
                st.success(f"Folder '{name}' created successfully!")
        except ValueError as e:
            st.error(str(e))


def ui_read_folder():
    st.subheader("📂 Workspace contents")
    items = list_items()
    if not items:
        st.info("The workspace is empty.")
        return
    rows = []
    for i, p in enumerate(items, start=1):
        rows.append(
            {
                "#": i,
                "Type": "📁 Folder" if p.is_dir() else "📄 File",
                "Path": str(p.relative_to(BASE)),
                "Size (bytes)": p.stat().st_size if p.is_file() else None,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def ui_update_folder():
    st.subheader("✏️ Rename a folder")
    folders = list_folders()
    if not folders:
        st.info("No folders to rename yet.")
        return
    old = st.selectbox("Select the folder to rename", folders)
    new = st.text_input("New folder name")
    if st.button("Rename folder", type="primary"):
        try:
            old_p, new_p = safe_path(old), safe_path(new)
            if new_p.exists():
                st.error("A folder/file with that name already exists.")
            else:
                old_p.rename(new_p)
                st.success("Updated successfully!")
                st.rerun()
        except ValueError as e:
            st.error(str(e))


def ui_delete_folder():
    st.subheader("🗑️ Delete a folder")
    folders = list_folders()
    if not folders:
        st.info("No folders to delete.")
        return
    name = st.selectbox("Select the folder to delete", folders)
    force = st.checkbox("Also delete everything inside it")
    confirm = st.checkbox("I understand this cannot be undone")
    if st.button("Delete folder", type="primary", disabled=not confirm):
        p = safe_path(name)
        try:
            if force:
                shutil.rmtree(p)
            else:
                p.rmdir()  # only works if empty
            st.success("Folder deleted successfully!")
            st.rerun()
        except OSError:
            st.error("Folder is not empty. Tick 'Also delete everything inside it'.")


# ---------------------------------------------------------------
# File operations
# ---------------------------------------------------------------
def ui_create_file():
    st.subheader("📝 Create a file")
    with st.form("create_file_form", clear_on_submit=True):
        name = st.text_input("File name with extension (e.g. `notes.txt`)")
        data = st.text_area("File content", height=200)
        submitted = st.form_submit_button("Create file", type="primary")
    if submitted:
        try:
            p = safe_path(name)
            if p.exists():
                st.error("File already exists. Please try again with another name.")
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(data, encoding="utf-8")
                st.success("File created successfully!")
        except ValueError as e:
            st.error(str(e))


def ui_read_file():
    st.subheader("📖 Read a file")
    files = list_files()
    if not files:
        st.info("No files yet.")
        return
    name = st.selectbox("Select a file to read", files)
    p = safe_path(name)
    try:
        content = p.read_text(encoding="utf-8")
        st.caption("Your file content is:")
        st.code(content or "(empty file)", language=None)
        st.download_button("Download file", content, file_name=p.name)
    except UnicodeDecodeError:
        st.warning("This looks like a binary file and can't be shown as text.")


def ui_update_file():
    st.subheader("🔧 Update a file")
    files = list_files()
    if not files:
        st.info("No files to update.")
        return
    name = st.selectbox("Select a file", files)
    p = safe_path(name)

    choice = st.radio(
        "Choose one option",
        ["Change the name", "Overwrite the file content", "Append new content"],
        horizontal=True,
    )

    if choice == "Change the name":
        new_name = st.text_input("New name with extension")
        if st.button("Rename file", type="primary"):
            try:
                new_p = safe_path(new_name)
                if new_p.exists():
                    st.error("A file with that name already exists.")
                else:
                    p.rename(new_p)
                    st.success("File name changed successfully!")
                    st.rerun()
            except ValueError as e:
                st.error(str(e))

    elif choice == "Overwrite the file content":
        try:
            current = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            st.warning("Binary file – can't edit as text.")
            return
        data = st.text_area("New content", value=current, height=250)
        if st.button("Overwrite", type="primary"):
            p.write_text(data, encoding="utf-8")
            st.success("Overwritten successfully!")

    else:  # append
        data = st.text_area("Content to append", height=150)
        if st.button("Append", type="primary"):
            with open(p, "a", encoding="utf-8") as fs:
                fs.write(data)
            st.success("Appended successfully!")


def ui_delete_file():
    st.subheader("🗑️ Delete a file")
    files = list_files()
    if not files:
        st.info("No files to delete.")
        return
    name = st.selectbox("Select the file to delete", files)
    confirm = st.checkbox("I understand this cannot be undone")
    if st.button("Delete file", type="primary", disabled=not confirm):
        safe_path(name).unlink()
        st.success("File deleted successfully!")
        st.rerun()


# ---------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------
st.title("🗂️ File & Folder Manager")
st.caption(f"Working inside: `{BASE_RESOLVED}`")

ACTIONS = {
    "📁 Create folder": ui_create_folder,
    "📂 Read folder": ui_read_folder,
    "✏️ Update folder": ui_update_folder,
    "🗑️ Delete folder": ui_delete_folder,
    "📝 Create file": ui_create_file,
    "📖 Read file": ui_read_file,
    "🔧 Update file": ui_update_file,
    "❌ Delete file": ui_delete_file,
}

with st.sidebar:
    st.header("Menu")
    choice = st.radio("What do you want to do?", list(ACTIONS.keys()))
    st.divider()
    st.metric("Folders", len(list_folders()))
    st.metric("Files", len(list_files()))

ACTIONS[choice]()