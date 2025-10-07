"""Single-command Streamlit entrypoint.

Run this from the repo root:

    streamlit run streamlit_app.py

It launches the Streamlit UI that lists projects, runs the pipeline, and shows
artifacts. Uses code from `src/sd_model/ui_streamlit.py`.
"""

from src.sd_model.ui_streamlit import main


if __name__ == "__main__":
    main()

