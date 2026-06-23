FROM python:3.11-slim

WORKDIR /ui

RUN pip install --no-cache-dir streamlit==1.40.0 httpx>=0.27.0 python-dotenv>=1.0.0

COPY ./ui .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
