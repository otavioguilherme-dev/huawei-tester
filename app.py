import streamlit as st
import requests

# --- CONFIGURAÇÃO LOCAL (Substitua pelos seus dados) ---
IMASTER_IP = "159.138.213.219"
PORTA_API = "18008"
USERNAME = "seu_usuario_api"
PASSWORD = "sua_senha_segura"

def obter_token():
    # Rota exata para o iMaster na porta 18008
    url = f"https://{IMASTER_IP}:{PORTA_API}/rest/plat/v1/auth/tokens"
    
    headers = {"Content-Type": "application/json"}
    payload = {"userName": USERNAME, "password": PASSWORD}
    
    requests.packages.urllib3.disable_warnings() 
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
        if response.status_code in [200, 201]:
            return response.json()['data']['token_id']
        else:
            st.error(f"Falha na autenticação. Status: {response.status_code}. Resposta: {response.text}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão com o iMaster: {e}")
        return None

def buscar_dados_localidade(nome_localidade, token):
    headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
    
    # Endpoint do Inventário de Sites
    url_site = f"https://{IMASTER_IP}:{PORTA_API}/controller/campus/v1/sdwan/net/sites?name={nome_localidade}"
    
    try:
        res_site = requests.get(url_site, headers=headers, verify=False, timeout=10)
        
        st.write("--- DEBUG SITE ---")
        st.json(res_site.json()) 
        
        dados_site = res_site.json().get('data')
        if not dados_site or len(dados_site) == 0:
            return None, f"Site '{nome_localidade}' não encontrado. Verifique maiúsculas e minúsculas."
            
        site_id = dados_site[0]['id']
        
        # Endpoint de Alarmes Ativos do Site
        url_alarmes = f"https://{IMASTER_IP}:{PORTA_API}/controller/campus/v1/alarms?siteId={site_id}&status=active"
        res_alarmes = requests.get(url_alarmes, headers=headers, verify=False, timeout=10)
        
        st.write("--- DEBUG ALARMES ---")
        st.json(res_alarmes.json())
        
        alarmes = res_alarmes.json().get('data', [])
        return alarmes, None
    except Exception as e:
        return None, f"Erro ao consultar dados: {e}"

# --- INTERFACE GRÁFICA ---
st.set_page_config(page_title="Troubleshooting iMaster", page_icon="🌐")
st.title("🌐 Portal de Troubleshooting - iMaster NCE")
st.write("Executando localmente com acesso direto à rede do iMaster.")

localidade_pesquisada = st.text_input("Nome da Localidade:")

if st.button("Analisar Ponto"):
    if not localidade_pesquisada:
        st.warning("Por favor, digite o nome de uma localidade.")
    else:
        with st.spinner("Autenticando e coletando dados..."):
            token = obter_token()
            if token:
                alarmes, erro = buscar_dados_localidade(localidade_pesquisada, token)
                if erro:
                    st.error(erro)
                elif len(alarmes) == 0:
                    st.success("✅ **STATUS: SAUDÁVEL**. Nenhum alarme ativo.")
                else:
                    st.error(f"❌ **STATUS: COM PROBLEMA ({len(alarmes)} alarme(s) ativo(s))**")
