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
    PORTA_API = "18008" # Porta padrão comum
    
    # Lista de todas as rotas possíveis de autenticação da Huawei
    rotas_para_testar = [
        f"https://{ip_limpo}:{PORTA_API}/v1/auth/tokens",                      # Rota 1: Campus Padrão
        f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens",                  # Rota 2: WAN / IP Core
        f"https://{ip_limpo}:{PORTA_API}/rest/plat/v1/auth/tokens"             # Rota 3: WAN Alternativa
    ]
    
    requests.packages.urllib3.disable_warnings() 
    
    # O loop vai testar uma por uma automaticamente
    for url in rotas_para_testar:
        try:
            response = requests.post(
                url, 
                json={"userName": USERNAME, "password": PASSWORD}, 
                headers={"Content-Type": "application/json"}, 
                verify=False, 
                timeout=4
            )
            
            # Se encontrar a rota certa (Status 200 ou 201), captura o Token
            if response.status_code in [200, 201]:
                st.success(f"🔗 Conectado com sucesso via rota: {url}")
                return response.json()['data']['token_id']
                
        except Exception:
            continue # Se der erro de timeout ou rede nesta rota, pula para a próxima
            
    # Se sair do loop e não encontrar nenhuma rota funcional:
    st.error("❌ Todas as rotas de API retornaram erro (404 ou Timeout). Verifique se o IP/Portas estão liberados no Firewall ou consulte o modelo exato do seu iMaster.")
    return None
def buscar_dados_localidade(nome_localidade, token):
    ip_limpo = limpar_ip(IMASTER_IP)
    PORTA_API = "18002"
    headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
    
    url_site = f"https://{ip_limpo}:{PORTA_API}/controller/campus/v1/sdwan/net/sites?name={nome_localidade}"
    
    try:
        res_site = requests.get(url_site, headers=headers, verify=False, timeout=10)
        
        # DEBUG: Mostra o JSON que o iMaster retornou para sabermos se o site existe
        st.write("--- DEBUG SITE ---")
        st.json(res_site.json()) 
        
        dados_site = res_site.json().get('data')
        if not dados_site or len(dados_site) == 0:
            return None, f"O iMaster respondeu, mas não encontrou nenhum site com o nome: '{nome_localidade}'. Verifique maiúsculas/minúsculas."
            
        site_id = dados_site[0]['id']
        url_alarmes = f"https://{ip_limpo}:{PORTA_API}/controller/campus/v1/alarms?siteId={site_id}&status=active"
        res_alarmes = requests.get(url_alarmes, headers=headers, verify=False, timeout=10)
        
        # DEBUG: Mostra os alarmes que o iMaster retornou para este ID de site
        st.write("--- DEBUG ALARMES ---")
        st.json(res_alarmes.json())
        
        alarmes = res_alarmes.json().get('data', [])
        return alarmes, None
    except Exception as e:
        return None, f"Erro ao consultar dados do site: {e}"

# --- 3. INTERFACE GRÁFICA ---
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
