with tab4:
        # 🔒 SECURE DATABASE VIEW
        # 1. Try to get password from secrets
        try:
            admin_pw = st.secrets["passwords"]["admin"]
        except (FileNotFoundError, KeyError):
            st.error("🚫 Security Config Missing. Please set up .streamlit/secrets.toml")
            st.stop()  # Stop execution if no secret is found

        # 2. Check Input (No hardcoded fallback)
        if st.text_input("Enter Admin Password", type="password", key="db_pass_input") == admin_pw: 
            st.success("✅ Access Granted")
            st.dataframe(st.session_state.master_db, use_container_width=True)
        else:
            st.info("🔒 Enter password to view raw database.")