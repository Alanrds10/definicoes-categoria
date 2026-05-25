# -*- coding: utf-8 -*-
"""
App Streamlit - Gerador Scanntech com Preview Interativo e Desembrulho de URLs
"""
import streamlit as st
import pandas as pd
from jinja2 import Template
import base64
import requests
import io
import zipfile
import os
from urllib.parse import urlparse, parse_qs, unquote

try:
    from weasyprint import HTML
except ImportError:
    st.error("Erro Crítico: WeasyPrint não instalado corretamente. Verifique o requirements.txt e o packages.txt.")

# --- FUNÇÕES DE SUPORTE E TRATAMENTO DE DADOS ---

def formatar_lista_html(texto):
    if pd.isna(texto) or not str(texto).strip():
        return "<ul><li>Nenhum item cadastrado.</li></ul>"
    linhas = [linha.strip().lstrip('•').lstrip('-').strip() for linha in str(texto).split('\n') if linha.strip()]
    return "<ul>" + "".join(f"<li>{linha}</li>" for linha in linhas) + "</ul>"

def limpar_url_google(url):
    """
    Detecta links de redirecionamento ou busca do Google Images,
    extrai e decodifica o link real do ativo final.
    """
    if pd.isna(url) or not str(url).strip():
        return ""
    
    url_str = str(url).strip()
    
    if "google.com/url" in url_str or "google.com/imgres" in url_str:
        try:
            parsed_url = urlparse(url_str)
            parametros = parse_qs(parsed_url.query)
            
            if 'url' in parametros:
                return unquote(parametros['url'][0])
            elif 'q' in parametros:
                return unquote(parametros['q'][0])
            elif 'imgurl' in parametros:
                return unquote(parametros['imgurl'][0])
        except Exception:
            return url_str 
            
    return url_str

def baixar_imagem_base64(url_planilha):
    """Trata a URL do Google, faz o download do ativo e converte para Base64"""
    url_limpa = limpar_url_google(url_planilha)
    
    if not url_limpa:
        return ""
    if not url_limpa.startswith('http'):
        return url_limpa 

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resposta = requests.get(url_limpa, headers=headers, timeout=5) 
        if resposta.status_code == 200:
            tipo_conteudo = resposta.headers.get('content-type', 'image/png')
            b64 = base64.b64encode(resposta.content).decode('utf-8')
            return f"data:{tipo_conteudo};base64,{b64}"
    except Exception:
        pass
    return ""

def carregar_arquivo_local_base64(caminho_arquivo):
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = caminho_arquivo.split('.')[-1].lower()
            tipo = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{tipo};base64,{b64}"
    return ""

def exibir_pdf_no_navegador(pdf_bytes):
    """Codifica o PDF gerado em Base64 e renderiza usando tag OBJECT para evitar bloqueios de CSP"""
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f"""
    <object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="800px">
        <div style="padding:20px; text-align:center; background:#FFF5F5; border:1px solid #FEB2B2; border-radius:4px;">
            <p style="color:#C53030; font-weight:bold; margin:0 0 10px 0;">Não foi possível renderizar o PDF diretamente na tela.</p>
            <p style="color:#4A5568; font-size:11px;">Isso ocorre por restrições de segurança do seu navegador. O arquivo está perfeito e pronto para o lote abaixo.</p>
        </div>
    </object>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- NÚCLEO DE GERAÇÃO INDIVIDUAL ---

def gerar_pdf_bytes(linha, jinja_template, df_colunas):
    codigo = str(linha.get('CODIGO_CATEGORIA', '')).strip()
    nome = str(linha.get('NOME_CATEGORIA', '')).strip()
    
    # DICIONÁRIO CORRIGIDO: Remoção dos operadores sintáticos inválidos
    contexto = {
        "nome_categoria": nome,
        "codigo_categoria": codigo,
        "definicao": linha.get('DEFINICAO', ''),
        "padrao_contenido": linha.get('PADRAO_CONTENIDO', ''),
        "padrao_descritivo": linha.get('PADRAO_DESCRITIVO', ''),
        
        "obs_contenido": linha['OBS_CONTENIDO'] if 'OBS_CONTENIDO' in df_colunas and pd.notna(linha['OBS_CONTENIDO']) else "",
        "obs_descritivo": linha['OBS_DESCRITIVO'] if 'OBS_DESCRITIVO' in df_colunas and pd.notna(linha['OBS_DESCRITIVO']) else "",
        
        "produtos_pertencem_html": formatar_lista_html(linha.get('PRODUTOS_PERTENCEM_TXT', '')),
        "produtos_nao_pertencem_html": formatar_lista_html(linha.get('PRODUTOS_NAO_PERTENCEM_TXT', '')),
        
        "foto_pertence_1_path": baixar_imagem_base64(linha.get('FOTO_PERTENCE_1_PATH', '')),
        "foto_pertence_1_desc": linha.get('FOTO_PERTENCE_1_DESC', '') if pd.notna(linha.get('FOTO_PERTENCE_1_DESC')) else "",
        "foto_pertence_2_path": baixar_imagem_base64(linha.get('FOTO_PERTENCE_2_PATH', '')),
        "foto_pertence_2_desc": linha.get('FOTO_PERTENCE_2_DESC', '') if pd.notna(linha.get('FOTO_PERTENCE_2_DESC')) else "",
        "foto_pertence_3_path": baixar_imagem_base64(linha.get('FOTO_PERTENCE_3_PATH', '')),
        "foto_pertence_3_desc": linha.get('FOTO_PERTENCE_3_DESC', '') if pd.notna(linha.get('FOTO_PERTENCE_3_DESC')) else "",
        
        "foto_nao_pertence_1_path": baixar_imagem_base64(linha.get('FOTO_NAO_PERTENCE_1_PATH', '')),
        "foto_nao_pertence_1_desc": linha.get('FOTO_NAO_PERTENCE_1_DESC', '') if pd.notna(linha.get('FOTO_NAO_PERTENCE_1_DESC')) else "",
        "foto_nao_pertence_2_path": baixar_imagem_base64(linha.get('FOTO_NAO_PERTENCE_2_PATH', '')),
        "foto_nao_pertence_2_desc": linha.get('FOTO_NAO_PERTENCE_2_DESC', '') if pd.notna(linha.get('FOTO_NAO_PERTENCE_2_DESC')) else "",
        "foto_nao_pertence_3_path": baixar_imagem_base64(linha.get('FOTO_NAO_PERTENCE_3_PATH', '')),
        "foto_nao_pertence_3_desc": linha.get('FOTO_NAO_PERTENCE_3_DESC', '') if pd.notna(linha.get('FOTO_NAO_PERTENCE_3_DESC')) else "",
    }
    
    html_renderizado = jinja_template.render(contexto)
    pdf_bytes = HTML(string=html_renderizado, base_url=".").write_pdf()
    
    nome_seguro = "".join(char for char in nome if char.isalnum() or char in (' ', '_', '-')).rstrip()
    nome_arquivo = f"Definicao_{codigo.replace('.', '_')}_{nome_seguro}.pdf"
    
    return pdf_bytes, nome_arquivo

# --- INTERFACE DE USUÁRIO (UI) ---

st.set_page_config(page_title="Scanntech - Gerador de Categorias", page_icon="📄", layout="wide")

st.title("Geração de Definições de Categoria")
st.markdown("Valide o design no Preview abaixo antes de processar todo o lote de definições.")

with st.sidebar:
    st.header("Base de Dados")
    upload_planilha = st.file_uploader("Subir Planilha (.xlsx)", type=["xlsx"])
    st.markdown("---")

if upload_planilha:
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_html = os.path.join(diretorio_atual, "HTML_CSS_DEFINICAO-DE-CATEGORIA.html")
    caminho_logo = os.path.join(diretorio_atual, "Logo Scanntech Versão Preferencial.png")
    
    if not os.path.exists(caminho_html):
        st.error(f"⚠️ Erro de Leitura: O arquivo '{caminho_html}' não foi encontrado.")
        st.stop()
        
    with open(caminho_html, "r", encoding="utf-8") as f:
        html_preparado = f.read()

    logo_b64 = carregar_arquivo_local_base64(caminho_logo)
    if logo_b64:
        html_preparado = html_preparado.replace('id vs/Logo Scanntech Versão Preferencial.png', logo_b64)
        html_preparado = html_preparado.replace('Logo Scanntech Versão Preferencial.png', logo_b64)

    jinja_template = Template(html_preparado)
    df = pd.read_excel(upload_planilha)
    
    col_esquerda, col_direita = st.columns([1, 2])
    
    with col_esquerda:
        st.subheader("1. Preview da Primeira Linha")
        st.write(f"**Categoria Testada:** {df.iloc[0].get('NOME_CATEGORIA', 'N/A')}")
        st.write(f"**Total Identificado:** {len(df)} categorias na planilha.")
        
        with st.spinner("Renderizando preview..."):
            primeira_linha = df.iloc[0]
            pdf_preview_bytes, _ = gerar_pdf_bytes(primeira_linha, jinja_template, df.columns)
        st.success("Preview gerado com sucesso!")
        
        st.markdown("---")
        st.subheader("2. Geração em Lote")
        st.write("Se o layout ao lado estiver correto, inicie a produção:")
        
        iniciar_lote = st.button("🚀 Gerar Pacote Completo (ZIP)", type="primary", use_container_width=True)
        
        if iniciar_lote:
            zip_buffer = io.BytesIO()
            barra_progresso = st.progress(0)
            status_texto = st.empty()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for index, linha in df.iterrows():
                    status_texto.text(f"Processando [{index+1}/{len(df)}]: {linha.get('NOME_CATEGORIA', '...')}")
                    
                    bytes_pdf, nome_arquivo = gerar_pdf_bytes(linha, jinja_template, df.columns)
                    zip_file.writestr(nome_arquivo, bytes_pdf)
                    
                    barra_progresso.progress((index + 1) / len(df))
            
            status_texto.text("✅ Pacote finalizado!")
            st.balloons()
            
            zip_buffer.seek(0)
            st.download_button(
                label="⬇️ Baixar Arquivo ZIP",
                data=zip_buffer,
                file_name="Scanntech_Categorias_Lote.zip",
                mime="application/zip",
                use_container_width=True
            )

    with col_direita:
        st.subheader("Visualizador do PDF")
        exibir_pdf_no_navegador(pdf_preview_bytes)

else:
    st.info("⬆️ Aguardando o upload da planilha na barra lateral.")