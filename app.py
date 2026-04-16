import streamlit as st
import requests
import xml.etree.ElementTree as ET
from openai import OpenAI
import time

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="AI Medical Assistant | GlobalInternet.py",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Custom CSS – Medical / Scientific Theme (clean, blue, green)
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f0f8ff 0%, #e6f2f0 100%);
    }
    h1, h2, h3 {
        color: #0b3b5f !important;
        font-weight: 700 !important;
    }
    .card {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        border: 1px solid #cce7e8;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 28px rgba(0,0,0,0.1);
    }
    .stButton button {
        background: #1a7f6b;
        color: white !important;
        border-radius: 40px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        border: none;
        transition: 0.2s;
    }
    .stButton button:hover {
        background: #0e5e4f;
        transform: scale(1.02);
    }
    .stTextArea textarea {
        border-radius: 15px;
        border: 1px solid #bdd4e7;
        font-size: 1rem;
    }
    [data-testid="stSidebar"] {
        background: #ffffffdd;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0,0,0,0.05);
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding: 1rem;
        color: #4a6a6a;
        font-size: 0.8rem;
    }
    .big-globe {
        font-size: 5rem;
        display: block;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .medium-globe {
        font-size: 3rem;
        display: inline-block;
        margin-right: 10px;
    }
    .login-container {
        max-width: 450px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 30px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        text-align: center;
    }
    .citation {
        font-size: 0.85rem;
        background: #f1f9f9;
        padding: 0.5rem;
        border-left: 4px solid #1a7f6b;
        margin: 0.5rem 0;
        border-radius: 10px;
    }
    .disclaimer {
        background: #fff3cd;
        padding: 0.8rem;
        border-radius: 12px;
        color: #856404;
        font-size: 0.8rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Authentication
# -----------------------------
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<span class="big-globe">🌐</span>', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>AI Medical Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>by GlobalInternet.py</p>", unsafe_allow_html=True)
    password = st.text_input("Enter password to access", type="password", key="login_pass")
    if st.button("Login", use_container_width=True):
        if password == "20082010":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Access denied.")
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Cached PubMed Search (uses st.cache_data to avoid repeated searches)
# -----------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def search_pubmed_cached(query, max_results):
    """Cached version of PubMed search"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    # Search for IDs
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={requests.utils.quote(query)}&retmax={max_results}&usehistory=y"
    try:
        resp = requests.get(search_url, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        id_list = [id_elem.text for id_elem in root.findall(".//Id")]
        if not id_list:
            return []
        # Fetch details
        fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
        fetch_resp = requests.get(fetch_url, timeout=15)
        fetch_resp.raise_for_status()
        tree = ET.fromstring(fetch_resp.content)
        articles = []
        for article in tree.findall(".//PubmedArticle"):
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title"
            abstract_elem = article.find(".//AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None and fore is not None:
                    authors.append(f"{fore.text} {last.text}")
                elif last is not None:
                    authors.append(last.text)
            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            journal_elem = article.find(".//Title")
            journal = journal_elem.text if journal_elem is not None else ""
            articles.append({
                "title": title,
                "abstract": abstract,
                "url": url,
                "authors": author_str,
                "journal": journal
            })
        return articles
    except Exception as e:
        st.error(f"PubMed search error: {e}")
        return []

# -----------------------------
# Main App
# -----------------------------
def main_app():
    with st.sidebar:
        st.markdown('<span class="medium-globe">🌐</span> **GlobalInternet.py**', unsafe_allow_html=True)
        st.markdown("---")
        api_key = st.text_input("🔑 OpenAI API Key", type="password", help="Enter your OpenAI API key. Get one from https://platform.openai.com/api-keys")
        if api_key:
            st.success("✅ API key loaded")
        else:
            st.warning("⚠️ Please enter your OpenAI API key")
        st.markdown("---")
        lang = st.radio("🌐 Language", ["English", "Español", "Français", "Kreyòl"], index=0)
        st.markdown("---")
        st.markdown("**Founder & CEO:**")
        st.markdown("Gesner Deslandes")
        st.markdown("📞 WhatsApp: (509) 4738-5663")
        st.markdown("📧 deslandes78@gmail.com")
        st.markdown("🌐 [Main Website](https://globalinternetsitepy-abh7v6tnmskxxnuplrdcgk.streamlit.app/)")
        st.markdown("---")
        st.markdown("### 💰 Pricing")
        st.markdown("**$149 USD** one‑time (full software package) or **$10 per analysis**")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.markdown("© 2025 GlobalInternet.py")
        st.markdown("All Rights Reserved")
    
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.markdown('<span class="medium-globe">🌐</span>', unsafe_allow_html=True)
    with col_title:
        st.markdown("# 🧪 AI Medical & Scientific Literature Assistant")
        st.markdown("**Ask a medical or scientific question – get answers from real research with citations.**")
    st.markdown("---")
    
    # Language texts
    if lang == "English":
        question_label = "💊 Your medical / scientific question"
        search_btn = "🔍 Search PubMed & Generate Answer"
        processing = "Searching PubMed and generating answer..."
        no_api_key = "Please enter your OpenAI API key in the sidebar."
        no_question = "Please enter a question."
        results_header = "📄 Retrieved Articles (used for answer)"
        answer_header = "🧠 AI-Generated Answer (with citations)"
        disclaimer_text = "⚠️ This tool is for informational purposes only. Always consult a qualified healthcare professional for medical advice."
        citation_label = "Citation"
    elif lang == "Español":
        question_label = "💊 Tu pregunta médica / científica"
        search_btn = "🔍 Buscar en PubMed y generar respuesta"
        processing = "Buscando en PubMed y generando respuesta..."
        no_api_key = "Por favor, ingresa tu clave API de OpenAI en la barra lateral."
        no_question = "Por favor, ingresa una pregunta."
        results_header = "📄 Artículos recuperados (usados para la respuesta)"
        answer_header = "🧠 Respuesta generada por IA (con citas)"
        disclaimer_text = "⚠️ Esta herramienta es solo para fines informativos. Siempre consulta a un profesional de la salud calificado."
        citation_label = "Cita"
    elif lang == "Français":
        question_label = "💊 Votre question médicale / scientifique"
        search_btn = "🔍 Rechercher sur PubMed et générer une réponse"
        processing = "Recherche sur PubMed et génération de réponse..."
        no_api_key = "Veuillez entrer votre clé API OpenAI dans la barre latérale."
        no_question = "Veuillez entrer une question."
        results_header = "📄 Articles récupérés (utilisés pour la réponse)"
        answer_header = "🧠 Réponse générée par IA (avec citations)"
        disclaimer_text = "⚠️ Cet outil est à titre informatif uniquement. Consultez toujours un professionnel de santé qualifié."
        citation_label = "Citation"
    else:
        question_label = "💊 Kesyon medikal / syantifik ou"
        search_btn = "🔍 Chèche nan PubMed epi jenere repons"
        processing = "Chèche nan PubMed epi jenere repons..."
        no_api_key = "Tanpri antre kle OpenAI API ou nan ba lateral la."
        no_question = "Tanpri antre yon kesyon."
        results_header = "📄 Atik yo jwenn (yo itilize pou repons lan)"
        answer_header = "🧠 Repons ki jenere pa AI (ak referans)"
        disclaimer_text = "⚠️ Zouti sa a se pou enfòmasyon sèlman. Toujou konsilte yon pwofesyonèl sante kalifye."
        citation_label = "Referans"
    
    question = st.text_area(question_label, height=100, placeholder="e.g., What is the efficacy of metformin in type 2 diabetes?")
    max_results = st.slider("Number of articles to retrieve", 3, 10, 3, 1)  # default 3 for speed
    
    if st.button(search_btn, use_container_width=True):
        if not question.strip():
            st.error(no_question)
        elif not api_key:
            st.error(no_api_key)
        else:
            # Progress tracking
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            # Step 1: Search PubMed
            progress_text.text("🔍 Searching PubMed...")
            progress_bar.progress(20)
            articles = search_pubmed_cached(question, max_results)
            
            if not articles:
                st.warning("No articles found. Try a different question.")
                progress_text.empty()
                progress_bar.empty()
            else:
                progress_bar.progress(50)
                progress_text.text("📄 Preparing context from articles...")
                
                # Display articles in expanders
                with st.expander(results_header, expanded=False):
                    for i, art in enumerate(articles, 1):
                        st.markdown(f"**{i}. {art['title']}**")
                        st.markdown(f"*{art['authors']}* | *{art['journal']}*")
                        st.markdown(f"📄 {art['abstract'][:300]}..." if len(art['abstract']) > 300 else f"📄 {art['abstract']}")
                        st.markdown(f"🔗 [PubMed]({art['url']})")
                        st.markdown("---")
                
                # Build context and citations
                context = ""
                citations = []
                for idx, art in enumerate(articles, 1):
                    context += f"Article {idx}: {art['title']}\nAbstract: {art['abstract']}\n\n"
                    citations.append(f"[{idx}] {art['title']}. {art['authors']}. {art['journal']}. {art['url']}")
                
                # Step 2: Ask OpenAI
                progress_bar.progress(70)
                progress_text.text("🧠 Generating AI answer...")
                
                client = OpenAI(api_key=api_key)
                system_prompt = """You are a medical and scientific research assistant. Answer the user's question based **only** on the provided PubMed article abstracts. If the abstracts do not contain enough information, say so clearly. Always cite the relevant article(s) by their number (e.g., [1], [2]) at the end of each sentence or paragraph. Do not invent facts outside the provided text. Keep the answer professional, concise, and helpful."""
                user_prompt = f"Question: {question}\n\nRelevant research abstracts:\n{context}"
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    answer = response.choices[0].message.content
                    
                    progress_bar.progress(100)
                    progress_text.text("✅ Complete!")
                    time.sleep(0.5)
                    progress_text.empty()
                    progress_bar.empty()
                    
                    st.markdown(f"## {answer_header}")
                    st.markdown(f'<div class="card">{answer}</div>', unsafe_allow_html=True)
                    
                    st.markdown("#### 📚 References")
                    for cit in citations:
                        st.markdown(f'<div class="citation">{cit}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f'<div class="disclaimer">{disclaimer_text}</div>', unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"OpenAI error: {e}")
                    progress_text.empty()
                    progress_bar.empty()
    
    st.markdown('<div class="footer">🌐 GlobalInternet.py – AI Medical Assistant. From Haiti to the world.</div>', unsafe_allow_html=True)

# -----------------------------
# Run login or main app
# -----------------------------
if not check_password():
    login()
else:
    main_app()
