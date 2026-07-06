import streamlit as st
import requests

# --- 1. VALIDAÇÃO DOS SECRETS ---
try:
    IMASTER_IP = st.secrets["IMASTER_IP"]
    USERNAME = st.secrets["USERNAME"]
    PASSWORD = st.secrets["PASSWORD"]
    config_ok = True
except Exception:
    config_ok = False

# --- FUNÇÃO AUXILIAR CORRIGIDA ---
def limpar_ip(ip):
    """Remove protocolos e barras caso tenham sido digitados por engano"""
    if not ip:
        return ""
    return ip.replace("https://", "").replace("http://", "").strip("/")

# --- 2. FUNÇÕES DE API ---
def obter_token():
    ip_limpo = limpar_ip(IMASTER_IP)
    
    # Lista otimizada incluindo a rota que funciona na porta 18008 constatada
    rotas_para_testar = [
        f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens",                  # Rota ideal (Porta 18008 WAN)
        f"https://{ip_limpo}:18002/v1/auth/tokens",                            # Rota Campus Padrão
        f"https://{ip_limpo}:18002/rest/plat/v1/auth/tokens"                   # Rota Alternativa
    ]
    
    requests.packages.urllib3.disable_warnings() 
    
    for url in rotas_para_testar:
        try:
            response = requests.post(
                url, 
                json={"userName": USERNAME, "password": PASSWORD}, 
                headers={"Content-Type": "application/json"}, 
                verify=False, 
                timeout=4
            )
            if response.status_code in [200, 201]:
                return response.json()['data']['token_id']
        except Exception:
            continue
            
    return None

@st.cache_data(ttl=300) # Guarda a lista por 5 minutos para performance
def listar_todos_os_sites(token):
    """Busca todas as localidades ativas no iMaster para gerar a lista"""
    ip_limpo = limpar_ip(IMASTER_IP)
    
    # Testa as duas portas principais para o inventário
    portas = ["18008", "18002"]
    for porta in portas:
        url = f"https://{ip_limpo}:{porta}/controller/campus/v1/sdwan/net/sites"
        headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                dados = response.json().get('data', [])
                # Mapeia Nome do Site -> ID do Site
                return {site['name']: site['id'] for site in dados if 'name' in site}
        except Exception:
            continue
    return {}

def buscar_alarmes_por_id(site_id, token):
    """Interroga os alarmes ativos diretamente pelo ID mapeado"""
    ip_limpo = limpar_ip(IMASTER_IP)
    portas = ["18008", "18002"]
    
    for porta in portas:
        url_alarmes = f"https://{ip_limpo}:{porta}/controller/campus/v1/alarms?siteId={site_id}&status=active"
        headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
        try:
            res_alarmes = requests.get(url_alarmes, headers=headers, verify=False, timeout=5)
            if res_alarmes.status_code == 200:
                alarmes = res_alarmes.json().get('data', [])
                return alarmes, None
        except Exception as e:
            last_error = e
            continue
    return None, f"Erro ao consultar dados de alarmes nas portas testadas: {last_error}"

# --- 3. INTERFACE GRÁFICA ---
st.set_page_config(page_title="Troubleshooting iMaster", page_icon="🌐")
st.title("🌐 Portal de Troubleshooting - iMaster NCE")

if not config_ok:
    st.error("⚠️ Configuração Incompleta! Você precisa adicionar IMASTER_IP, USERNAME e PASSWORD nos 'Secrets' do Streamlit.")
else:
    # 1. Tenta autenticar e gerar a lista de pontos no início do carregamento da página
    with st.spinner("Autenticando e sincronizando lista de pontos ativos..."):
        token_atual = obter_token()
        if token_atual:
            dicionario_sites = listar_todos_os_sites(token_atual)
        else:
            dicionario_sites = {}
            st.error("❌ Falha na autenticação do iMaster. Verifique suas credenciais de API nos Secrets.")

    # 2. Se encontrou sites, renderiza o selectbox inteligente
    if dicionario_sites:
        st.write("Selecione um ponto abaixo no menu para iniciar a análise automatizada de quedas e perdas.")
        
        lista_nomes = sorted(list(dicionario_sites.keys()))
        site_selecionado = st.selectbox("Selecione a Localidade para Consulta:", lista_nomes)
        
        if st.button("Analisar Saúde do Ponto"):
            id_do_site = dicionario_sites[site_selecionado]
            
            with st.spinner(f"Interrogando alarmes de {site_selecionado}..."):
                alarmes, erro = buscar_alarmes_por_id(id_do_site, token_atual)
                
                if erro:
                    st.error(erro)
                elif len(alarmes) == 0:
                    st.success(f"✅ **STATUS: SAUDÁVEL**. O ponto **{site_selecionado}** está operando normalmente sem alarmes.")
                else:
