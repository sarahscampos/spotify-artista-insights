import streamlit as st
import pandas as pd
import spotipy
import plotly.express as px
from spotipy.oauth2 import SpotifyClientCredentials

st.set_page_config(
    page_title="Spotify Insights",
    page_icon="https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png", # Ícone do Spotify
    layout="wide"
)

CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]

st.markdown("""
    <style>
    /* Cor de fundo do site */
    .main { 
        background-color: #f5f5f5; 
    }
    
    /* Desenho do cartão branco */
    [data-testid="stMetric"] { 
        background-color: #1ED760; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1); 
    }
    
    /* Forçando o título da métrica a ficar cinza escuro */
    [data-testid="stMetricLabel"] p {
        color: #121212 !important;
    }
    
    /* Forçando o número da métrica a ficar preto */
    [data-testid="stMetricValue"] div {
        color: #121212 !important;
        font-weight: bold;
    }

  
    /* Reset geral de cores para Selectbox e Input */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] {
        border-color: #333333 !important; /* Cor da borda quando não está clicado */
        transition: border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out !important;
    }

    /* Aplica o Verde Spotify ao clicar e mantém durante a transição */
    div[data-baseweb="select"] > div:focus-within, 
    div[data-baseweb="input"]:focus-within {
        border-color: #1ED760 !important;
        box-shadow: 0 0 0 1px #1ED760 !important;
    }

   
    :root {
        --primary-color: #1ED760;
    }

    
    div[data-baseweb="select"]:hover, 
    div[data-baseweb="input"]:hover {
        border-color: #1ED760 !important;
    }
    
    /* Estilização do texto e cursor */
    input {
        caret-color: #1ED760 !important;
    }
   

    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def conectar_spotify():
    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, cache_handler=spotipy.cache_handler.MemoryCacheHandler())
    return spotipy.Spotify(auth_manager=auth_manager)

sp = conectar_spotify()
st.sidebar.title("Configurações")
id_input = st.sidebar.text_input(
    "Cole o ID do Artista do Spotify:", 
    value="1sPg5EHuQXTMElpZ4iUgXe" # ID da Anavitória como padrão
)

# Limpa o ID caso o usuário cole o link completo do navegador
artist_id = id_input.split('/')[-1].split('?')[0]

@st.cache_data(ttl=86400) # Guarda por 1 hora
def buscar_dados_artista(id_artista):
    return sp.artist(id_artista)

@st.cache_data(ttl=86400)
def buscar_albuns(id_artista):
    res = sp.artist_albums(id_artista, album_type='album', limit=10)
    # Filtra nomes únicos
    unicos = {}
    for a in res['items']:
        if a['name'] not in unicos:
            unicos[a['name']] = a
    return unicos

@st.cache_data(ttl=86400)
def buscar_faixas_album(id_album):
    faixas_brutas = []
    offset = 0
    while True:
        res = sp.album_tracks(id_album, limit=10, offset=offset)
        faixas_brutas.extend(res['items'])
        if not res['next']: break
        offset += 10
    return faixas_brutas

if artist_id:

    try:
    
        artista = buscar_dados_artista(artist_id)
        albuns_unicos = buscar_albuns(artist_id)
        
        # --- HEADER ---
        st.markdown(
        f"""
        <h1 style='display: flex; align-items: center;'>
            <img src='https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png' 
                style='width:60px; margin-right:5px;'>
            {artista['name']}
        </h1>
        """, 
        unsafe_allow_html=True
    )
        st.write("Exploração completa de catálogo e colaborações.")

        # --- SIDEBAR E SELEÇÃO ---
        st.sidebar.image(artista['images'][0]['url'], width=200)
        album_nome = st.sidebar.selectbox("Selecione o Álbum:", list(albuns_unicos.keys()))
        album_info = albuns_unicos[album_nome]

        # --- PROCESSAMENTO DAS MÚSICAS DO ÁLBUM ---
        faixas_brutas = buscar_faixas_album(album_info['id'])

        dados_lista = []
        colaboradores = []

        for f in faixas_brutas:
            duracao_ms = f['duration_ms']
            
            # Converte milissegundos para minutos e segundos 
            minutos = duracao_ms // 60000
            segundos = (duracao_ms % 60000) // 1000
            
            # Cria a string formatada "M:SS"
            tempo_formatado = f"{minutos}:{segundos:02d}"
            
            # Para o gráfico, ainda precisamos do valor numérico (em minutos decimais)
            duracao_decimal = round(duracao_ms / 60000, 2)
            
            artistas_na_pista = [a['name'] for a in f['artists']]
            tem_feat = "Sim" if len(artistas_na_pista) > 1 else "Não"
            
            if len(artistas_na_pista) > 1:
                convidados = [a for a in artistas_na_pista if artista['name'].upper() not in a.upper()]
                colaboradores.extend(convidados)

            dados_lista.append({
                "Música": f['name'],
                "Duração": tempo_formatado,       # O que vai aparecer na tabela
                "Duração (min)": duracao_decimal, # O que vai para o gráfico
                "Feat": tem_feat,
                "Convidados": ", ".join([a for a in artistas_na_pista if artista['name'].upper() not in a.upper()])
            })

        df = pd.DataFrame(dados_lista)

        # --- MÉTRICAS DE RESUMO (KPIs) ---
        m1, m2, m3 = st.columns(3)
        total_ms = sum([f['duration_ms'] for f in faixas_brutas])
        min_totais = int(total_ms // 60000)
        
        m1.metric("Duração Total do Álbum", f"{min_totais} min")
        m2.metric("Média por Faixa", f"{round(df['Duração (min)'].mean(), 2)} min")
        m3.metric("Músicas com Feat", len(df[df['Feat'] == "Sim"]))

        st.divider()

        # --- COLUNAS PRINCIPAIS ---
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Player & Capa")
            st.image(album_info['images'][0]['url'], width=350)
            album_id = album_info['id']
            st.markdown(f'<iframe src="https://open.spotify.com/embed/album/{album_id}" style="border-radius:12px" width="100%" height="152" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>', unsafe_allow_html=True)

        with col2:
            st.subheader("Análise de Faixas")
            df_display = df[['Música', 'Duração', 'Feat']].copy()
            df_display.index = df_display.index + 1
        
            st.dataframe(df_display, width='stretch')
            
            if colaboradores:
                st.write("**Colaboradores neste álbum:** " + ", ".join(list(set(colaboradores))))
            else:
                st.write("*Este é um álbum totalmente solo.*")

        # --- GRÁFICOS INFERIORES ---
        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Variabilidade de Tempo")
            # Criamos o gráfico usando Plotly Express
            fig_line = px.line(
                df, 
                x="Música", 
                y="Duração (min)",
                color_discrete_sequence=["#1ED760"] 
            )
            
            fig_line.update_xaxes(tickangle=45)
            
            fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            
            st.plotly_chart(fig_line, width='stretch')

        with c2:
            st.subheader("Proporção de Feats")
            # Criamos os dados para o gráfico de barras
            feat_counts = df['Feat'].value_counts().reset_index()
            feat_counts.columns = ['Feat', 'Quantidade']
            
            fig_bar = px.bar(
                feat_counts, 
                x="Feat", 
                y="Quantidade",
                color_discrete_sequence=["#1ED760"]
            )
            
            fig_bar.update_xaxes(tickangle=0)
            
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            
            st.plotly_chart(fig_bar, width='stretch')

    except Exception as e:
        st.error(f"Erro na conexão: {e}")

else:
    # Mensagem amigável caso o campo esteja vazio
    st.warning("Por favor, insira um ID de artista válido na barra lateral para começar.")
    st.info("Dica: Você pode encontrar o ID no link do artista no Spotify (ex: spotify:artist:ID_AQUI)")