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

def limpar_ip(ip):
    if not ip:
        return ""
    return ip.replace("https://", "").replace("http://", "").strip("/")

# --- 2. FUNÇÕES DE API ---
def obter_token():
    ip_limpo = limpar_ip(IMASTER_IP)
    
    # Lista expandida com as rotas oficiais de operadoras/WAN da Huawei
    combinacoes = [
        # 1. Rota Direta (Comum no iMaster NCE IP/Transporte na porta 18008)
        {"url": f"https://{ip_limpo}:18008/rest/v1/auth/tokens", "tipo": "wan_direto"},
        
        # 2. Rota de Assinatura/Token de Segurança OpenAPI Huawei
        {"url": f"https://{ip_limpo}:18008/rest/openapi/v1/signature", "tipo": "signature"},
        
        # 3. Rotas anteriores (mantidas para cobertura)
        {"url": f"https://{ip_limpo}:18008/rest/openapi/v1/auth/tokens", "tipo": "openapi"},
        {"url": f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens", "tipo": "wan_estrito"},
        {"url": f"https://{ip_limpo}:18002/v1/auth/tokens", "tipo": "campus"}
    ]
    
    requests.packages.urllib3.disable_warnings() 
    erros_tentativas = []
    
    for item in combinacoes:
        url = item["url"]
        
        if item["tipo"] == "wan_estrito":
            payload = {"authParams": {"userName": USERNAME, "password": PASSWORD}}
        else:
            payload = {"userName": USERNAME, "password": PASSWORD}
            
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, verify=False, timeout=5)
            if response.status_code in [200, 201]:
                dados = response.json()
                
                # Garante a captura do Token independente do nome da chave retornada
                for chave_data in ['data', 'authResult']:
                    if chave_data in dados and 'token_id' in dados[chave_data]:
                        return dados[chave_data]['token_id']
                    if chave_data in dados and 'token' in dados[chave_data]:
                        return dados[chave_data]['token']
                        
                if 'token' in dados: return dados['token']
                if 'access_token' in dados: return dados['access_token']
                if 'token_id' in dados: return dados['token_id']
            else:
                erros_tentativas.append(f"Rota {url} retornou HTTP {response.status_code}")
        except Exception as e:
            erros_tentativas.append(f"Rota {url} falhou: {e}")
            continue
            
    st.session_state['erros_login'] = erros_tentativas
    return None
@st.cache_data(ttl=300)
def listar_todos_os_elementos(token):
    ip_limpo = limpar_ip(IMASTER_IP)
    headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
    
    # Rota 1: OpenAPI Nodes
    url_openapi = f"https://{ip_limpo}:18008/rest/openapi/network/v1/nodes"
    try:
        response = requests.get(url_openapi, headers=headers, verify=False, timeout=5)
        if response.status_code == 200:
            dados = response.json().get('data', [])
            if dados: return {node['name']: node['id'] for node in dados if 'name' in node}
    except Exception: pass

    # Rota 2: RESTCONF
    url_ne = f"https://{ip_limpo}:18008/rest/netconf-data/v1/network-elements"
    try:
        response = requests.get(url_ne, headers=headers, verify=False, timeout=5)
        if response.status_code == 200:
            dados = response.json().get('network-elements', {}).get('network-element', [])
            if dados: return {ne['name']: ne['ne-id'] for ne in dados if 'name' in ne}
    except Exception: pass
        
    return {}

# --- 3. INTERFACE GRÁFICA ---
st.set_page_config(page_title="O&M iMaster Huawei", page_icon="🌐")
st.title("🌐 Portal de Troubleshooting Inteligente - Huawei iMaster")

if not config_ok:
    st.error("⚠️ Configuração Incompleta nos Secrets do Streamlit.")
else:
    token_atual = None
    dicionario_pontos = {}

    with st.spinner("Conectando ao barramento de API do iMaster..."):
        token_atual = obter_token()
        if token_atual:
            dicionario_pontos = listar_todos_os_elements(token_atual)

    # SE CONECTOU E TROUXE ELEMENTOS
    if dicionario_pontos:
        st.success(f"Sucesso! {len(dicionario_pontos)} localidades mapeadas.")
        lista_nomes = sorted(list(dicionario_pontos.keys()))
        ponto_selecionado = st.selectbox("Selecione o Ponto/Circuito para Análise:", lista_nomes)
    
    # SE FALHOU EM TUDO (Evita a tela em branco que aconteceu na imagem)
    else:
        if not token_atual:
            st.error("❌ Falha crítica de Autenticação. Nenhuma rota de login funcionou.")
            if 'erros_login' in st.session_state:
                with st.expander("Clique aqui para ver o log técnico do erro"):
                    for err in st.session_state['erros_login']:
                        st.code(err)
        else:
            st.warning("⚠️ Conectado com sucesso, mas o inventário de equipamentos retornou vazio (Verifique as permissões do seu usuário no iMaster).")
