import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import json
import os
import re
from datetime import datetime
import tempfile
import io

# Try to import PDF/DOCX libraries, handle if not installed
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="AI Resume Screening System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .qualified-badge {
        background-color: #28a745;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin-left: 10px;
    }
    .not-qualified-badge {
        background-color: #dc3545;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin-left: 10px;
    }
    .skill-match {
        background-color: #d4edda;
        color: #155724;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
        margin: 2px;
        display: inline-block;
    }
    .skill-missing {
        background-color: #f8d7da;
        color: #721c24;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
        margin: 2px;
        display: inline-block;
    }
    .candidate-name {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
    }
    .resume-preview {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        font-family: monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)


# ==================== RESUME TEXT EXTRACTION ====================

def extract_text_from_pdf(file):
    """Extract text from PDF file."""
    if not PDF_AVAILABLE:
        return "ERROR: PyPDF2 not installed. Run: pip install PyPDF2"
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text if text.strip() else "ERROR: Could not extract text from PDF (possibly scanned image)"
    except Exception as e:
        return f"ERROR reading PDF: {str(e)}"

def extract_text_from_docx(file):
    """Extract text from DOCX file."""
    if not DOCX_AVAILABLE:
        return "ERROR: python-docx not installed. Run: pip install python-docx"
    try:
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text if text.strip() else "ERROR: Empty DOCX file"
    except Exception as e:
        return f"ERROR reading DOCX: {str(e)}"

def extract_text_from_txt(file):
    """Extract text from TXT file."""
    try:
        return file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"ERROR reading TXT: {str(e)}"

def extract_resume_text(file):
    """Extract text from any resume file type."""
    file_extension = file.name.lower().split(".")[-1]
    file.seek(0)
    
    if file_extension == "pdf":
        return extract_text_from_pdf(file)
    elif file_extension == "docx":
        return extract_text_from_docx(file)
    elif file_extension == "txt":
        return extract_text_from_txt(file)
    else:
        return f"ERROR: Unsupported file format: {file_extension}"


# ==================== SKILL & CONTENT EXTRACTION ====================

# Comprehensive skills database - ALL DOUBLE QUOTES to avoid apostrophe issues
SKILLS_DATABASE = [
    # Programming Languages
    "Python", "Java", "JavaScript", "C++", "C#", "C", "Ruby", "Go", "Golang", "Rust", 
    "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Shell", "Bash", "PowerShell",
    "TypeScript", "Dart", "Lua", "Julia", "Haskell", "Cobol", "Fortran", "Assembly",
    
    # Web Development
    "HTML", "CSS", "React", "Angular", "Vue", "Vue.js", "Node.js", "Express", "Django", 
    "Flask", "FastAPI", "Spring", "Spring Boot", "Laravel", "Rails", "ASP.NET", "Next.js",
    "Nuxt.js", "Svelte", "jQuery", "Bootstrap", "Tailwind CSS", "WordPress", "Drupal",
    
    # Databases
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Oracle", "SQLite", "Redis", "Cassandra",
    "DynamoDB", "Firebase", "Elasticsearch", "Neo4j", "MariaDB", "CouchDB", "Snowflake",
    
    # Data Science & AI
    "Machine Learning", "Deep Learning", "AI", "Artificial Intelligence", "Data Science",
    "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Scikitlearn", "Pandas", "NumPy", 
    "SciPy", "Matplotlib", "Seaborn", "Plotly", "OpenCV", "NLTK", "SpaCy", "Hugging Face",
    "XGBoost", "LightGBM", "CatBoost", "Statsmodels", "Jupyter", "Anaconda",
    
    # Big Data
    "Spark", "Apache Spark", "Hadoop", "Kafka", "Airflow", "Databricks", "Hive", "Pig",
    "Flink", "Storm", "MapReduce", "HBase", "Presto", "BigQuery", "ETL",
    
    # Cloud & DevOps
    "AWS", "Amazon Web Services", "Azure", "Microsoft Azure", "GCP", "Google Cloud", 
    "Docker", "Kubernetes", "K8s", "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI",
    "Travis CI", "Terraform", "Ansible", "Puppet", "Chef", "Vagrant", "Prometheus", "Grafana",
    "ELK Stack", "Nginx", "Apache", "Tomcat", "IIS", "CloudFormation", "Serverless",
    "Lambda", "EC2", "S3", "RDS", "Azure DevOps", "Heroku", "Netlify", "Vercel",
    
    # Mobile Development
    "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic", "Cordova", "PhoneGap",
    "SwiftUI", "Jetpack Compose", "Objective-C",
    
    # Tools & Others
    "Git", "GitHub", "GitLab", "Bitbucket", "SVN", "Jira", "Confluence", "Trello", "Slack",
    "REST API", "GraphQL", "SOAP", "gRPC", "WebSocket", "Microservices", "Serverless",
    "OAuth", "JWT", "SAML", "LDAP", "Active Directory", "Selenium", "Cypress", "Jest",
    "Mocha", "PyTest", "JUnit", "TestNG", "Cucumber", "Postman", "Swagger", "OpenAPI",
    "Figma", "Adobe XD", "Sketch", "Photoshop", "Illustrator", "InDesign", "Premiere",
    "After Effects", "Blender", "Unity", "Unreal Engine", "Godot", "Maya", "3ds Max",
    
    # Soft Skills
    "Leadership", "Management", "Communication", "Teamwork", "Problem Solving",
    "Critical Thinking", "Agile", "Scrum", "Kanban", "Waterfall", "SDLC", "Project Management",
    "Product Management", "Business Analysis", "Data Analysis", "Data Analytics",
    "Business Intelligence", "Tableau", "Power BI", "Qlik", "Looker", "Excel", "VBA",
    "SAP", "Salesforce", "CRM", "ERP", "Oracle ERP", "Workday", "ServiceNow",
    "Cybersecurity", "Penetration Testing", "Ethical Hacking", "CISSP", "CEH", "CompTIA",
    "Network Security", "Firewall", "IDS", "IPS", "SIEM", "SOC", "ISO 27001", "GDPR",
    "HIPAA", "PCI DSS", "NIST", "COBIT", "ITIL", "Six Sigma", "Lean", "PMP", "Prince2",
    "TOGAF", "Zachman", "ArchiMate", "BPMN", "UML", "SysML",
    "RPA", "UiPath", "Automation Anywhere", "Blue Prism", "Power Automate",
    "Blockchain", "Ethereum", "Solidity", "Hyperledger", "Smart Contracts", "Web3",
    "IoT", "Raspberry Pi", "Arduino", "Embedded Systems", "RTOS", "Firmware",
    "PLC", "SCADA", "Industrial Automation", "Robotics", "ROS", "Computer Vision",
    "NLP", "Natural Language Processing", "Speech Recognition", "OCR", "Recommender Systems",
    "Time Series", "Forecasting", "Anomaly Detection", "Clustering", "Classification",
    "Regression", "Neural Networks", "CNN", "RNN", "LSTM", "GRU", "Transformer", "BERT",
    "GPT", "LLM", "Large Language Models", "Generative AI", "Prompt Engineering",
    "MLOps", "Data Engineering", "Data Architecture", "Data Modeling", "Data Warehouse",
    "Data Lake", "Lakehouse", "Delta Lake", "dbt", "Airbyte", "Fivetran", "Stitch",
    "Matillion", "Talend", "Informatica", "SSIS", "SSRS", "SSAS", "Power Pivot",
    "DAX", "MDX", "SQL Server", "T-SQL", "PL/SQL", "NoSQL", "NewSQL", "GraphQL",
    "Neo4j", "ArangoDB", "OrientDB", "Amazon Neptune", "Gremlin", "Cypher",
    "CockroachDB", "TiDB", "YugabyteDB", "PlanetScale", "Vitess", "ProxySQL",
    "PgBouncer", "Redis Sentinel", "Redis Cluster", "KeyDB", "Dragonfly",
    "ClickHouse", "Apache Druid", "Pinot", "Trino", "PrestoDB", "DuckDB",
    "MotherDuck", "Supabase", "Appwrite", "Directus", "Strapi", "Contentful",
    "Sanity", "Prismic", "Ghost", "Medium", "Substack", "Webflow",
    "Shopify", "Magento", "WooCommerce", "BigCommerce", "Stripe", "PayPal",
    "Square", "Adyen", "Braintree", "Razorpay", "Paytm", "PhonePe", "UPI",
    "Plaid", "Yodlee", "MX", "Finicity", "TrueLayer", "Open Banking", "PSD2",
    "KYC", "AML", "Fraud Detection", "Risk Management", "Credit Scoring",
    "Algorithmic Trading", "Quantitative Finance", "Portfolio Management",
    "Bloomberg Terminal", "Reuters Eikon", "FactSet", "Capital IQ", "PitchBook",
    "Crunchbase", "LinkedIn Sales Navigator", "HubSpot", "Marketo", "Pardot",
    "Mailchimp", "Klaviyo", "Iterable", "Braze", "Customer.io", "SendGrid",
    "Twilio", "MessageBird", "Vonage", "Nexmo", "Plivo", "Sinch", "Bandwidth",
    "Agora", "Daily.co", "100ms", "Mux", "Cloudflare Stream", "AWS Elemental",
    "Azure Media Services", "Google Cloud Video", "FFmpeg", "GStreamer", "WebRTC",
    "RTMP", "HLS", "DASH", "CMAF", "SRT", "RIST", "Zixi", "NDI", "SDI", "HDMI",
    "DisplayPort", "USB", "Thunderbolt", "PCIe", "NVMe", "SATA", "SAS", "FC",
    "iSCSI", "NFS", "SMB", "CIFS", "AFP", "FTP", "SFTP", "SCP", "RSYNC",
    "Rclone", "Syncthing", "Resilio", "Dropbox", "Google Drive", "OneDrive",
    "Box", "iCloud", "Nextcloud", "OwnCloud", "Seafile", "Pydio", "FileCloud",
    "Egnyte", "ShareFile", "Citrix", "VMware", "Hyper-V", "KVM", "Xen", "Proxmox",
    "VirtualBox", "Parallels", "QEMU", "libvirt", "oVirt", "OpenStack", "CloudStack",
    "Eucalyptus", "Nutanix", "VMware vSphere", "vCenter", "ESXi", "NSX", "vSAN",
    "Horizon", "Workspace ONE", "Intune", "SCCM", "MDM", "EMM", "UEM",
    "AirWatch", "MobileIron", "SOTI", "Hexnode", "Scalefusion", "Miradore",
    "Addigy", "Kandji", "Jamf", "FileWave", "Fleetsmith", "Mosyle", "JumpCloud",
    "Okta", "Auth0", "OneLogin", "Ping Identity", "ForgeRock", "CyberArk",
    "BeyondTrust", "Thycotic", "Delinea", "Secret Server", "Passwordstate",
    "Keeper", "LastPass", "1Password", "Bitwarden", "Dashlane", "NordPass",
    "RoboForm", "Enpass", "KeePass", "Passbolt", "Teampass", "Psono",
    "Keycloak", "Authentik", "Authelia", "Dex", "OAuth2 Proxy", "Vouch",
    "Pomerium", "Teleport", "Boundary", "StrongDM", "BastionZero", "Aker",
    "Twingate", "Tailscale", "ZeroTier", "Netmaker", "Headscale", "Innernet",
    "Nebula", "WireGuard", "OpenVPN", "IPsec", "L2TP", "PPTP", "SSTP", "IKEv2",
    "SoftEther", "Algo", "Streisand", "Shadowsocks", "V2Ray", "Xray", "Trojan",
    "Clash", "Surge", "Quantumult", "Shadowrocket", "Potatso", "Pharos", "OneClick",
    "Outline", "Cloak", "Snowflake", "Tor", "I2P", "Freenet", "ZeroNet", "IPFS",
    "Filecoin", "Arweave", "Storj", "Sia", "MaidSafe", "SAFE Network", "Holochain",
    "BigchainDB", "Chainlink", "Band Protocol", "API3", "The Graph", "Covalent",
    "Moralis", "Alchemy", "Infura", "QuickNode", "Pocket Network", "Ankr",
    "Chainstack", "GetBlock", "BlockDaemon", "Figment", "Bison Trails", "Stakefish",
    "Lido", "Rocket Pool", "Stakewise", "Frax", "Curve", "Convex", "Yearn",
    "Aave", "Compound", "MakerDAO", "Uniswap", "SushiSwap", "PancakeSwap",
    "Trader Joe", "Raydium", "Orca", "Serum", "Jupiter", "1inch", "Matcha",
    "Paraswap", "CowSwap", "Balancer", "Gnosis", "CoW Protocol", "MEV",
    "Flashbots", "Eden Network", "BloxRoute", "Manifold", "Blocknative",
    "Tenderly", "OpenZeppelin", "Hardhat", "Truffle", "Brownie", "Foundry",
    "DappTools", "Scaffold-ETH", "useDapp", "Wagmi", "RainbowKit", "ConnectKit",
    "Web3Modal", "WalletConnect", "MetaMask", "Coinbase Wallet", "Phantom",
    "Solflare", "Slope", "Torus", "Portis", "Fortmatic", "Magic", "Web3Auth",
    "Safe", "Gnosis Safe", "Argent", "Loopring", "zkSync", "StarkNet", "Arbitrum",
    "Optimism", "Polygon", "Avalanche", "Fantom", "Harmony", "Cronos", "Celo",
    "Moonbeam", "Moonriver", "Astar", "Shiden", "Acala", "Karura", "Polkadot",
    "Kusama", "Substrate", "Ink", "Cosmos", "Tendermint", "IBC", "Osmosis",
    "Juno", "Secret", "Akash", "Persistence", "Kava", "Injective", "Band",
    "Terra", "Luna", "Anchor", "Mirror", "Pylon", "Astroport", "Mars",
    "Nexus", "Prism", "Stader", "Quicksilver", "Stride", "Persistence",
    "AssetMantle", "OmniFlix", "Stargaze", "Regen", "CertiK", "Quantstamp",
    "Trail of Bits", "OpenZeppelin", "ConsenSys Diligence", "Runtime Verification",
    "Formal Verification", "Model Checking", "Symbolic Execution", "Fuzzing",
    "Static Analysis", "Dynamic Analysis", "SAST", "DAST", "IAST", "RASP",
    "WAF", "DDoS Protection", "Bot Management", "Fraud Prevention", "Bot Detection",
    "CAPTCHA", "reCAPTCHA", "hCaptcha", "Arkose", "GeeTest", "FunCaptcha",
    "DataDome", "PerimeterX", "Imperva", "Akamai", "Cloudflare", "Fastly",
    "StackPath", "KeyCDN", "BunnyCDN", "CDN77", "BelugaCDN", "G-Core Labs",
    "QUIC.cloud", "Litespeed", "Nginx", "Apache", "Caddy", "Traefik",
    "Envoy", "HAProxy", "Varnish", "Squid", "ATS", "Nuster", "Pound",
    "Stud", "Stunnel", "OpenSSL", "LibreSSL", "BoringSSL", "WolfSSL",
    "mbed TLS", "GnuTLS", "NSS", "MatrixSSL", "Botan", "Crypto++",
    "libsodium", "OpenPGP", "GPG", "PGP", "S/MIME", "DKIM", "SPF",
    "DMARC", "BIMI", "MTA-STS", "TLS-RPT", "DANE", "DNSSEC", "DoH",
    "DoT", "DoQ", "ECH", "ESNI", "SNI", "ALPN", "OCSP", "CRL", "CT",
    "Certificate Transparency", "Let's Encrypt", "Certbot", "ACME",
    "ZeroSSL", "BuyPass", "SSL.com", "DigiCert", "Sectigo", "GlobalSign",
    "Entrust", "IdenTrust", "GoDaddy", "Namecheap", "Cloudflare SSL",
    "AWS Certificate Manager", "Azure Key Vault", "Google Cloud KMS",
    "HashiCorp Vault", "CyberArk Conjur", "AWS Secrets Manager",
    "Azure App Configuration", "Google Secret Manager", "Doppler",
    "1Password Secrets", "Bitwarden Secrets", "Infisical", "Vaultwarden",
    "Passbolt", "Teampass", "Psono", "Keycloak", "Authentik", "Authelia"
]

def extract_skills_from_resume(text):
    """Extract skills that actually exist in the resume text."""
    text_lower = text.lower()
    found_skills = []
    
    for skill in SKILLS_DATABASE:
        # Use word boundary matching to avoid partial matches
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.append(skill)
    
    return found_skills

def extract_skills_from_job_description(text):
    """Extract skills mentioned in job description."""
    return extract_skills_from_resume(text)

def match_skills(resume_skills, job_skills):
    """Find matched and missing skills."""
    matched = [s for s in job_skills if s in resume_skills]
    missing = [s for s in job_skills if s not in resume_skills]
    extra = [s for s in resume_skills if s not in job_skills]
    return matched, missing, extra


# ==================== MAIN UI CLASS ====================

class ResumeScreeningUI:
    """Streamlit UI for AI Resume Screening System."""
    
    def __init__(self):
        self._init_session_state()
    
    def _init_session_state(self):
        if "job_description" not in st.session_state:
            st.session_state.job_description = ""
        if "resumes" not in st.session_state:
            st.session_state.resumes = []
        if "results" not in st.session_state:
            st.session_state.results = None
        if "settings" not in st.session_state:
            st.session_state.settings = {
                "provider": "OpenAI",
                "model": "gpt-4",
                "weights": {
                    "skills": 0.35,
                    "experience": 0.30,
                    "education": 0.20,
                    "certifications": 0.15
                },
                "threshold": 60
            }
        if "processing" not in st.session_state:
            st.session_state.processing = False
    
    def _extract_name_from_resume(self, resume_text, filename):
        """Extract candidate name from resume text or filename."""
        name_patterns = [
            r"[Nn]ame\s*[:\\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"[Ff]ull\s*[Nn]ame\s*[:\\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*\n",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[-–]\s*(?:Resume|CV|Curriculum)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, resume_text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        name = os.path.splitext(filename)[0]
        name = name.replace("_", " ").replace("-", " ").title()
        return name if name else "Unknown Candidate"
    
    def _extract_email_from_resume(self, resume_text):
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, resume_text)
        return match.group(0) if match else "N/A"
    
    def _extract_experience_years(self, text):
        patterns = [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"(\d+)[\s-]*(?:to)?[\s-]*\d*\s*years?",
            r"experience\s*(?:of\s*)?(\d+)\s*years?"
        ]
        max_years = 0
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    years = int(match)
                    max_years = max(max_years, years)
                except:
                    pass
        return max_years
    
    def _extract_education_score(self, text):
        text_lower = text.lower()
        if any(word in text_lower for word in ["phd", "ph.d", "doctorate"]):
            return 100
        elif any(word in text_lower for word in ["master", "mba", "m.s", "m.tech", "m.sc"]):
            return 85
        elif any(word in text_lower for word in ["bachelor", "b.tech", "b.e", "b.sc", "b.s", "undergraduate"]):
            return 70
        elif any(word in text_lower for word in ["diploma", "associate"]):
            return 50
        else:
            return 40
    
    def _extract_certification_score(self, text):
        cert_keywords = ["certified", "certification", "aws certified", "google certified", 
                        "microsoft certified", "oracle certified", "pmp", "scrum", "aws", 
                        "azure", "gcp", "docker", "kubernetes", "ci/cd"]
        text_lower = text.lower()
        cert_count = sum(1 for cert in cert_keywords if cert in text_lower)
        return min(cert_count * 15, 100)
    
    def _generate_recommendation(self, score, matched_count, missing_count):
        if score >= 80:
            return "Excellent match! Strongly recommend for interview."
        elif score >= 60:
            return f"Good match ({matched_count} skills matched). Consider for interview."
        elif score >= 40:
            return f"Partial match ({matched_count}/{matched_count+missing_count} skills). Review further."
        else:
            return f"Weak match ({missing_count} missing skills). Not recommended."
    
    def _render_settings(self):
        st.title("Settings")
        st.markdown("---")
        
        st.subheader("Model Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            model_provider = st.selectbox(
                "Model Provider",
                ["OpenAI", "Anthropic", "Local/Ollama", "Azure OpenAI"],
                index=["OpenAI", "Anthropic", "Local/Ollama", "Azure OpenAI"].index(
                    st.session_state.settings.get("provider", "OpenAI")
                ),
                key="settings_provider"
            )
        
        with col2:
            model_name = st.text_input(
                "Model Name",
                value=st.session_state.settings.get("model", "gpt-4"),
                key="settings_model_name"
            )
        
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="Enter your API key",
            value=st.session_state.settings.get("api_key", ""),
            key="settings_api_key"
        )
        
        st.markdown("---")
        st.subheader("Scoring Weights")
        col1, col2, col3, col4 = st.columns(4)
        
        current_weights = st.session_state.settings.get("weights", {})
        
        with col1:
            skills_weight = st.slider("Skills", 0.0, 1.0, current_weights.get("skills", 0.35), key="weight_skills")
        with col2:
            exp_weight = st.slider("Experience", 0.0, 1.0, current_weights.get("experience", 0.30), key="weight_exp")
        with col3:
            edu_weight = st.slider("Education", 0.0, 1.0, current_weights.get("education", 0.20), key="weight_edu")
        with col4:
            cert_weight = st.slider("Certifications", 0.0, 1.0, current_weights.get("certifications", 0.15), key="weight_cert")
        
        total = skills_weight + exp_weight + edu_weight + cert_weight
        if abs(total - 1.0) > 0.01:
            st.warning(f"Weights sum to {total:.2f}. Should be 1.0")
        else:
            st.success(f"Weights sum to {total:.2f}")
        
        st.markdown("---")
        st.subheader("Qualification Threshold")
        match_threshold = st.slider("Minimum Score to Qualify (%)", 0, 100, st.session_state.settings.get("threshold", 60), key="settings_threshold")
        st.caption(f"Candidates scoring >= {match_threshold}% will be marked as Qualified")
        
        st.markdown("---")
        
        if st.button("Save Settings", type="primary", key="btn_save_settings"):
            st.session_state.settings = {
                "provider": model_provider,
                "model": model_name,
                "api_key": api_key,
                "weights": {
                    "skills": skills_weight,
                    "experience": exp_weight,
                    "education": edu_weight,
                    "certifications": cert_weight
                },
                "threshold": match_threshold
            }
            st.success("Settings saved!")
            st.balloons()
    
    def _render_input_section(self):
        st.markdown("### Job Description")
        
        job_desc = st.text_area(
            "Paste the job description here",
            value=st.session_state.job_description,
            height=200,
            placeholder="Enter the job description, requirements, and qualifications...",
            key="job_desc_input"
        )
        
        if job_desc != st.session_state.job_description:
            st.session_state.job_description = job_desc
        
        st.markdown("---")
        st.markdown("### Upload Resumes")
        
        if not PDF_AVAILABLE:
            st.warning("PyPDF2 not installed. PDF support disabled. Run: pip install PyPDF2")
        if not DOCX_AVAILABLE:
            st.warning("python-docx not installed. DOCX support disabled. Run: pip install python-docx")
        
        uploaded_files = st.file_uploader(
            "Upload resume files (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="resume_uploader"
        )
        
        if uploaded_files:
            st.session_state.resumes = uploaded_files
            st.success(f"{len(uploaded_files)} resume(s) uploaded successfully!")
            
            with st.expander("Preview Extracted Text"):
                for file in uploaded_files:
                    text = extract_resume_text(file)
                    st.markdown(f"**{file.name}:**")
                    st.markdown(f'<div class="resume-preview">{text[:500]}...</div>', unsafe_allow_html=True)
        
        if st.session_state.resumes:
            st.markdown("**Uploaded Files:**")
            for i, file in enumerate(st.session_state.resumes, 1):
                preview_name = os.path.splitext(file.name)[0].replace("_", " ").replace("-", " ").title()
                st.write(f"{i}. **{preview_name}** ({file.size:,} bytes)")
    
    def _render_results_section(self):
        st.markdown("### Screening Results")
        
        if st.session_state.results is None:
            st.info("Upload job description and resumes, then click Screen Resumes to see results")
            return
        
        results = st.session_state.results
        threshold = st.session_state.settings.get("threshold", 60)
        
        qualified = [r for r in results if r.get("score", 0) >= threshold]
        not_qualified = [r for r in results if r.get("score", 0) < threshold]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Candidates", len(results))
        with col2:
            avg_score = np.mean([r.get("score", 0) for r in results]) if results else 0
            st.metric("Average Score", f"{avg_score:.1f}%")
        with col3:
            st.metric("Qualified", len(qualified))
        with col4:
            st.metric("Not Qualified", len(not_qualified))
        with col5:
            top_score = max([r.get("score", 0) for r in results]) if results else 0
            st.metric("Top Score", f"{top_score:.1f}%")
        
        st.markdown("---")
        
        if qualified:
            st.subheader(f"Qualified Candidates (Score >= {threshold}%)")
            for i, candidate in enumerate(qualified, 1):
                self._render_candidate_card(candidate, i, threshold, is_qualified=True)
        
        if not_qualified:
            st.subheader(f"Not Qualified (Score < {threshold}%)")
            for i, candidate in enumerate(not_qualified, 1):
                self._render_candidate_card(candidate, i, threshold, is_qualified=False)
    
    def _render_candidate_card(self, candidate, rank, threshold, is_qualified):
        score = candidate.get("score", 0)
        name = candidate.get("name", "Unknown Candidate")
        email = candidate.get("email", "N/A")
        
        if score >= 80:
            border_color = "#28a745"
            bg_color = "#d4edda"
        elif score >= threshold:
            border_color = "#ffc107"
            bg_color = "#fff3cd"
        else:
            border_color = "#dc3545"
            bg_color = "#f8d7da"
        
        badge_class = "qualified-badge" if is_qualified else "not-qualified-badge"
        badge_text = "QUALIFIED" if is_qualified else "NOT QUALIFIED"
        
        st.markdown(f"""
        <div style="border: 2px solid {border_color}; background-color: {bg_color}; 
                    border-radius: 10px; padding: 15px; margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; flex-wrap: wrap;">
                        <span class="candidate-name">#{rank} {name}</span>
                        <span class="{badge_class}">{badge_text}</span>
                    </div>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9rem;">{email}</p>
                </div>
                <div style="text-align: right; min-width: 120px;">
                    <h2 style="margin: 0; color: {border_color}; font-size: 2rem;">{score:.1f}%</h2>
                    <p style="margin: 0; font-size: 0.8rem; color: #666;">Match Score</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("View Full Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Matched Skills (in both resume and job):**")
                matched_skills = candidate.get("matched_skills", [])
                if matched_skills:
                    for skill in matched_skills:
                        st.markdown(f'<span class="skill-match">{skill}</span>', unsafe_allow_html=True)
                else:
                    st.write("No matching skills found")
            
            with col2:
                st.markdown("**Missing Skills (in job but NOT in resume):**")
                missing_skills = candidate.get("missing_skills", [])
                if missing_skills:
                    for skill in missing_skills:
                        st.markdown(f'<span class="skill-missing">{skill}</span>', unsafe_allow_html=True)
                else:
                    st.write("No missing skills - all required skills found!")
            
            st.markdown("**All Skills Found in Resume:**")
            all_skills = candidate.get("all_skills", [])
            if all_skills:
                for skill in all_skills:
                    st.markdown(f'<span style="background-color: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 12px; font-size: 0.85rem; margin: 2px; display: inline-block;">{skill}</span>', unsafe_allow_html=True)
            else:
                st.warning("No recognizable skills found in this resume")
            
            st.markdown("**Score Breakdown:**")
            breakdown = candidate.get("breakdown", {})
            if breakdown:
                breakdown_data = []
                for category, score_val in breakdown.items():
                    weight = st.session_state.settings["weights"].get(category, 0.25)
                    weighted_score = score_val * weight
                    breakdown_data.append({
                        "Category": category.title(),
                        "Raw Score": f"{score_val:.1f}%",
                        "Weight": f"{weight:.2f}",
                        "Weighted": f"{weighted_score:.1f}%"
                    })
                
                breakdown_df = pd.DataFrame(breakdown_data)
                st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
            
            st.markdown("**Experience Summary:**")
            st.write(candidate.get("experience_summary", "No experience summary available"))
            
            st.markdown("**Education:**")
            st.write(candidate.get("education", "No education details available"))
            
            st.markdown("**Recommendation:**")
            rec = candidate.get("recommendation", "No recommendation available")
            if is_qualified:
                st.success(rec)
            else:
                st.warning(rec)
    
    def _screen_resumes(self):
        """Process and screen resumes against job description with REAL extraction."""
        if not st.session_state.job_description:
            st.error("Please enter a job description first!")
            return
        
        if not st.session_state.resumes:
            st.error("Please upload at least one resume!")
            return
        
        if not PDF_AVAILABLE and not DOCX_AVAILABLE:
            st.error("Cannot read PDF or DOCX files. Please install: pip install PyPDF2 python-docx")
            return
        
        st.session_state.processing = True
        
        with st.spinner("Reading resume contents and analyzing..."):
            results = []
            
            job_skills = extract_skills_from_job_description(st.session_state.job_description)
            st.info(f"Found {len(job_skills)} skills in job description: {', '.join(job_skills[:10])}{'...' if len(job_skills) > 10 else ''}")
            
            for i, resume_file in enumerate(st.session_state.resumes):
                resume_text = extract_resume_text(resume_file)
                
                if resume_text.startswith("ERROR"):
                    st.error(f"Failed to read {resume_file.name}: {resume_text}")
                    continue
                
                real_name = self._extract_name_from_resume(resume_text, resume_file.name)
                real_email = self._extract_email_from_resume(resume_text)
                
                resume_skills = extract_skills_from_resume(resume_text)
                
                matched_skills, missing_skills, extra_skills = match_skills(resume_skills, job_skills)
                
                total_required = len(job_skills)
                if total_required > 0:
                    skill_score = (len(matched_skills) / total_required) * 100
                else:
                    skill_score = 50
                
                exp_years = self._extract_experience_years(resume_text)
                exp_score = min(exp_years * 10, 100) if exp_years > 0 else 30
                
                edu_score = self._extract_education_score(resume_text)
                cert_score = self._extract_certification_score(resume_text)
                
                weights = st.session_state.settings["weights"]
                total_score = (
                    skill_score * weights["skills"] +
                    exp_score * weights["experience"] +
                    edu_score * weights["education"] +
                    cert_score * weights["certifications"]
                )
                
                total_score = max(0, min(100, total_score))
                
                result = {
                    "name": real_name,
                    "email": real_email,
                    "score": total_score,
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "extra_skills": extra_skills,
                    "all_skills": resume_skills,
                    "breakdown": {
                        "skills": skill_score,
                        "experience": exp_score,
                        "education": edu_score,
                        "certifications": cert_score
                    },
                    "experience_summary": f"{exp_years} years of experience" if exp_years > 0 else "Experience not specified in resume",
                    "education": self._extract_education_text(resume_text),
                    "recommendation": self._generate_recommendation(total_score, len(matched_skills), len(missing_skills)),
                }
                results.append(result)
            
            results.sort(key=lambda x: x["score"], reverse=True)
            st.session_state.results = results
        
        st.session_state.processing = False
        threshold = st.session_state.settings.get("threshold", 60)
        qualified_count = len([r for r in results if r["score"] >= threshold])
        st.success(f"Analysis complete! {qualified_count} out of {len(results)} candidates qualified.")
        
        with st.expander("Debug: Extracted Skills Summary"):
            for r in results:
                st.write(f"**{r['name']}**: Found {len(r['all_skills'])} skills total | Matched: {len(r['matched_skills'])} | Missing: {len(r['missing_skills'])}")
    
    def _extract_education_text(self, text):
        edu_patterns = [
            r"(?:education|academic|qualification)[\s\S]*?(?=(?:experience|skills|projects|achievements|$))",
            r"(?:b\.?tech|b\.?e\.?|m\.?tech|m\.?s\.?|mba|ph\.?d)[\s\S]*?(?=\n\n|\Z)"
        ]
        for pattern in edu_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)[:200].strip()
        return "Education details not found in resume"
    
    def _render_sidebar(self):
        with st.sidebar:
            st.markdown("## Controls")
            st.markdown("---")
            
            if st.button("Screen Resumes", type="primary", use_container_width=True):
                self._screen_resumes()
            
            st.markdown("---")
            
            if st.button("Clear All", use_container_width=True):
                st.session_state.job_description = ""
                st.session_state.resumes = []
                st.session_state.results = None
                st.rerun()
            
            st.markdown("---")
            
            if st.session_state.results:
                if st.button("Export Results", use_container_width=True):
                    export_data = []
                    threshold = st.session_state.settings.get("threshold", 60)
                    for r in st.session_state.results:
                        export_data.append({
                            "Rank": 0,
                            "Name": r.get("name", "Unknown"),
                            "Email": r.get("email", "N/A"),
                            "Score (%)": f"{r.get('score', 0):.1f}",
                            "Status": "QUALIFIED" if r.get("score", 0) >= threshold else "NOT QUALIFIED",
                            "Matched Skills": ", ".join(r.get("matched_skills", [])),
                            "Missing Skills": ", ".join(r.get("missing_skills", [])),
                            "All Skills": ", ".join(r.get("all_skills", [])),
                            "Recommendation": r.get("recommendation", "")
                        })
                    
                    export_df = pd.DataFrame(export_data)
                    export_df["Rank"] = range(1, len(export_df) + 1)
                    
                    csv = export_df.to_csv(index=False)
                    st.download_button("Download CSV", csv, "screening_results.csv", "text/csv", use_container_width=True)
            
            st.markdown("---")
            threshold = st.session_state.settings.get("threshold", 60)
            st.info(f"Current Qualification Threshold: **{threshold}%**")
            
            st.markdown("### About")
            st.write("""
            This AI-powered resume screening system:
            - Extracts REAL skills from resume text
            - Compares with job requirements
            - Shows only actual skills found
            - No fake or random data
            """)
            
            st.markdown("---")
            st.caption("v2.1 | Real Resume Parser")
    
    def run(self):
        st.markdown('<h1 class="main-header">AI Resume Screening System</h1>', unsafe_allow_html=True)
        self._render_sidebar()
        
        tab1, tab2, tab3 = st.tabs(["Input", "Results", "Settings"])
        
        with tab1:
            self._render_input_section()
        
        with tab2:
            self._render_results_section()
        
        with tab3:
            self._render_settings()


def main():
    ui = ResumeScreeningUI()
    ui.run()


if __name__ == "__main__":
    main()
