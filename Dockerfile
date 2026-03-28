FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir streamlit requests python-dotenv gtts groq

EXPOSE 8501

CMD ["streamlit", "run", "01_scout_module/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
