# NetSage AI - Streamlit setup

## Windows
1. Extract the entire ZIP folder.
2. Open the extracted `NetSage-AI-main` folder.
3. In File Explorer, click the address bar, type `cmd`, and press Enter.
4. Run:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`.

## AI diagnosis (optional)
The deterministic rule checker works without an API key. To enable Groq AI diagnosis, get a Groq API key and set it in the same terminal before starting Streamlit:

```powershell
$env:GROQ_API_KEY="your_actual_key_here"
python -m streamlit run app.py
```

Do not publish or commit your API key. The app does not apply network changes; it only offers diagnosis and suggested steps. Verify suggestions before using them.
