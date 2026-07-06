import streamlit as st
import requests

# --- 1. VALIDAÇÃO DOS SECRETS ---
# Evita que o app quebre se você esquecer de configurar os Secrets no painel
try:
    IMASTER_IP = st.secrets["IMASTER_IP"]
    USERNAME = st.secrets["USERNAME"]
    PASSWORD = st.secrets["PASSWORD"]
    config_ok = True
except Exception:
    config_ok = False

# --- 2. FUNÇÕES DE API ---
def obter_token():
    url = f"https://{IMASTER_IP}:18002/v1/auth/tokens"
    headers = {"Content-Type": "application/json"}
    payload = {"userName": USERNAME, "password": PASSWORD}
    requests.packages.urllib3.disable_warnings() 
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=5)
        if response.status_code in [200, 201]:
            return response.json()['data']['token_id']
    except Exception as e:
        st.error(f"Erro de conexão com o iMaster: {e}")
        return None
    return None

def buscar_dados_localidade(nome_localidade, token):
    headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
    url_site = f"https://{IMASTER_IP}:18002/controller/campus/v1/sdwan/net/sites?name={nome_localidade}"
    
    try:
        res_site = requests.get(url_site, headers=headers, verify=False, timeout=5)
        if not res_site.json().get('data'):
            return None, "Localidade não encontrada no inventário do iMaster."
            
        site_id = res_site.json()['data'][0]['id']
        url_alarmes = f"https://{IMASTER_IP}:18002/controller/campus/v1/alarms?siteId={site_id}&status=active"
        res_alarmes = requests.get(url_alarmes, headers=headers, verify=False, timeout=5)
        alarmes = res_alarmes.json().get('data', [])
        return alarmes, None
    except Exception as e:
        return None, f"Erro ao consultar dados: {e}"

# --- 3. INTERFACE GRÁFICA (Sempre renderiza) ---
st.set_page_config(page_title="Troubleshooting iMaster", page_icon="🌐")
st.title("🌐 Portal de Troubleshooting - iMaster NCE")

if not config_ok:
    st.error("⚠️ Configuração Incompleta! Você precisa adicionar IMASTER_IP, USERNAME e PASSWORD nos 'Secrets' do Streamlit Cloud.")
else:
    st.write("Digite o nome da localidade para analisar a saúde do ponto.")
    
    localidade_pesquisada = st.text_input("Nome da Localidade:")
    
    if st.button("Analisar Ponto"):
        if not localidade_pesquisada:
            st.warning("Por favor, digite o nome de uma localidade.")
        else:
            with st.spinner("Conectando ao iMaster NCE..."):
                token = obter_token()
                if token:
                    alarmes, erro = buscar_dados_localidade(localidade_pesquisada, token)
                    if erro:
                        st.error(erro)
                    elif len(alarmes) == 0:
                        st.success("✅ **STATUS: SAUDÁVEL**. Nenhum alarme ativo.")
                    else:
                        st.error(f"❌ **STATUS: COM PROBLEMA ({len(alarmes)} alarme(s) ativo(s))**")
                        st.write(alarmes)
