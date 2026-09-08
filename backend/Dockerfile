# Build-Kontext ist das Repo-Wurzelverzeichnis (siehe docker-compose*.yml),
# damit die Regeln aus prompts/ mit ins Image kommen: config.PROMPT_DATEI
# zeigt auf ../prompts/rezept_buddy.md = /prompts/rezept_buddy.md. Ein leeres
# benanntes Volume auf /prompts wird beim ersten Start aus dem Image befuellt,
# danach schreibt der Coach-Editor dort hinein und ueberlebt Rebuilds.
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY prompts/ /prompts/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
