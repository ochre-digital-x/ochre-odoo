FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 MCP_TRANSPORT=http
WORKDIR /app
COPY pyproject.toml README.md ./
COPY ochre_odoo_mcp ./ochre_odoo_mcp
RUN pip install --no-cache-dir . && useradd -r -u 10001 app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["ochre-odoo-mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
