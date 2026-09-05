Create VM : python -m venv libraryAdmin
goto VM : cd libraryAdmin
Activate VM : .\libraryAdmin\Scripts\Activate.ps1
python -m pip install requests
python -m pip list
python -m pip freeze > requirements.txt
python -m pip install -r requirements.txt

install streamlit : python -m pip install streamlit