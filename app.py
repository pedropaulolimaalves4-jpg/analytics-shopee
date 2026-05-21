from flask import Flask, redirect, request, render_template_string, jsonify, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)

BANCO = "cliques.db"

def conectar():
    return sqlite3.connect(BANCO)

def criar_banco():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT,
            categoria TEXT,
            preco TEXT,
            score INTEGER,
            link_destino TEXT,
            criado_em TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cliques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER,
            produto TEXT,
            categoria TEXT,
            ip TEXT,
            user_agent TEXT,
            horario TEXT
        )
    """)

    conexao.commit()
    conexao.close()

def registrar_link(produto, categoria, preco, score, link_destino):
    criar_banco()

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT id FROM links WHERE link_destino = ?",
        (link_destino,)
    )

    existente = cursor.fetchone()

    if existente:
        conexao.close()
        return existente[0]

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    cursor.execute("""
        INSERT INTO links (
            produto,
            categoria,
            preco,
            score,
            link_destino,
            criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        produto,
        categoria,
        preco,
        score,
        link_destino,
        agora
    ))

    link_id = cursor.lastrowid

    conexao.commit()
    conexao.close()

    return link_id

@app.route("/")
def inicio():
    criar_banco()

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT COUNT(*) FROM links")
    total_links = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cliques")
    total_cliques = cursor.fetchone()[0]

    cursor.execute("""
        SELECT produto, categoria, COUNT(*) as total
        FROM cliques
        GROUP BY produto, categoria
        ORDER BY total DESC
        LIMIT 20
    """)
    ranking = cursor.fetchall()

    cursor.execute("""
        SELECT categoria, COUNT(*) as total
        FROM cliques
        GROUP BY categoria
        ORDER BY total DESC
        LIMIT 10
    """)
    categorias = cursor.fetchall()

    cursor.execute("""
        SELECT horario, produto, categoria
        FROM cliques
        ORDER BY id DESC
        LIMIT 15
    """)
    recentes = cursor.fetchall()

    conexao.close()

    html = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="30">
        <title>Analytics de Cliques</title>
        <style>
            body { font-family: Arial, sans-serif; background: #111827; color: #f9fafb; padding: 30px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
            .card { background: #1f2937; padding: 20px; border-radius: 14px; margin-bottom: 20px; }
            h1, h2 { color: #fbbf24; }
            table { width: 100%; border-collapse: collapse; background: #1f2937; border-radius: 14px; overflow: hidden; margin-bottom: 28px; }
            th, td { padding: 12px; border-bottom: 1px solid #374151; text-align: left; }
            th { color: #fbbf24; }
            .numero { font-size: 34px; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🔥 Analytics de Cliques</h1>
        <p><a style="color:#fbbf24" href="/export/cliques.json">Exportar cliques</a> | <a style="color:#fbbf24" href="/export/links.json">Exportar links</a> | <a style="color:#fbbf24" href="/health">Status</a></p>

        <div class="grid">
            <div class="card"><h2>Links</h2><div class="numero">{{ total_links }}</div></div>
            <div class="card"><h2>Cliques</h2><div class="numero">{{ total_cliques }}</div></div>
        </div>

        <h2>Produtos mais clicados</h2>
        <table>
            <tr><th>Produto</th><th>Categoria</th><th>Cliques</th></tr>
            {% for produto, categoria, total in ranking %}
            <tr><td>{{ produto }}</td><td>{{ categoria }}</td><td>{{ total }}</td></tr>
            {% endfor %}
        </table>

        <h2>Categorias mais clicadas</h2>
        <table>
            <tr><th>Categoria</th><th>Cliques</th></tr>
            {% for categoria, total in categorias %}
            <tr><td>{{ categoria }}</td><td>{{ total }}</td></tr>
            {% endfor %}
        </table>

        <h2>Últimos cliques</h2>
        <table>
            <tr><th>Horário</th><th>Produto</th><th>Categoria</th></tr>
            {% for horario, produto, categoria in recentes %}
            <tr><td>{{ horario }}</td><td>{{ produto }}</td><td>{{ categoria }}</td></tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """

    return render_template_string(
        html,
        total_links=total_links,
        total_cliques=total_cliques,
        ranking=ranking,
        categorias=categorias,
        recentes=recentes
    )

@app.route("/r/<int:link_id>")
def redirecionar(link_id):
    criar_banco()

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT produto, categoria, link_destino
        FROM links
        WHERE id = ?
    """, (link_id,))

    resultado = cursor.fetchone()

    if not resultado:
        conexao.close()
        return "Link não encontrado.", 404

    produto, categoria, link_destino = resultado

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "")
    horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    cursor.execute("""
        INSERT INTO cliques (
            link_id,
            produto,
            categoria,
            ip,
            user_agent,
            horario
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        link_id,
        produto,
        categoria,
        ip,
        user_agent,
        horario
    ))

    conexao.commit()
    conexao.close()

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Abrindo oferta...</title>

        <style>
            body {{
                background: #111827;
                color: white;
                font-family: Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                text-align: center;
                padding: 20px;
            }}

            .box {{
                background: #1f2937;
                padding: 30px;
                border-radius: 18px;
                max-width: 420px;
                width: 100%;
                box-shadow: 0 0 25px rgba(0,0,0,0.4);
            }}

            h1 {{
                color: #fbbf24;
                margin-bottom: 14px;
            }}

            p {{
                color: #d1d5db;
                line-height: 1.5;
            }}

            .botao {{
                display: inline-block;
                margin-top: 20px;
                background: #f59e0b;
                color: black;
                font-weight: bold;
                padding: 14px 22px;
                border-radius: 12px;
                text-decoration: none;
                transition: 0.2s;
            }}

            .botao:hover {{
                transform: scale(1.04);
            }}
        </style>

        <script>
            setTimeout(function() {{
                window.open("{link_destino}", "_self");
            }}, 800);
        </script>
    </head>

    <body>
        <div class="box">
            <h1>🔥 Abrindo oferta...</h1>

            <p>
                Abrindo oferta na Shopee...
            </p>

            <a class="botao" href="{link_destino}">
                🛒 Abrir oferta
            </a>
        </div>
    </body>
    </html>
    """

    return html

@app.route("/novo", methods=["POST"])
def novo_link():
    criar_banco()

    dados = request.get_json(force=True)

    produto = dados.get("produto", "Produto")
    categoria = dados.get("categoria", "ofertas")
    preco = dados.get("preco", "")
    score = int(dados.get("score", 0))
    link_destino = dados.get("link_destino", "")

    if not link_destino:
        return {"erro": "link_destino vazio"}, 400

    link_id = registrar_link(
        produto=produto,
        categoria=categoria,
        preco=preco,
        score=score,
        link_destino=link_destino
    )

    base_url = request.host_url.rstrip("/")

    return {
        "id": link_id,
        "link_rastreado": f"{base_url}/r/{link_id}"
    }

@app.route("/export/cliques.json")
def exportar_cliques_json():
    criar_banco()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT id, link_id, produto, categoria, ip, user_agent, horario
        FROM cliques
        ORDER BY id ASC
    """)
    linhas = cursor.fetchall()
    conexao.close()

    dados = []
    for linha in linhas:
        dados.append({
            "id": linha[0],
            "link_id": linha[1],
            "produto": linha[2],
            "categoria": linha[3],
            "ip": linha[4],
            "user_agent": linha[5],
            "horario": linha[6]
        })

    return jsonify(dados)

@app.route("/export/links.json")
def exportar_links_json():
    criar_banco()
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT id, produto, categoria, preco, score, link_destino, criado_em
        FROM links
        ORDER BY id ASC
    """)
    linhas = cursor.fetchall()
    conexao.close()

    dados = []
    for linha in linhas:
        dados.append({
            "id": linha[0],
            "produto": linha[1],
            "categoria": linha[2],
            "preco": linha[3],
            "score": linha[4],
            "link_destino": linha[5],
            "criado_em": linha[6]
        })

    return jsonify(dados)

@app.route("/health")
def health():
    return {"status": "online", "servico": "analytics-shopee"}

if __name__ == "__main__":
    criar_banco()
    app.run(host="0.0.0.0", port=5000)
