"""Quick test to verify agent works with mainframe data."""

from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

from enterprise_assistant.agents.enterprise_agent import create_enterprise_agent

print("🔧 Creating agent and loading mainframe files...")
mainframe_dir = Path(__file__).parent / "sample_mainframe"
agent = create_enterprise_agent(
    documents_dir=mainframe_dir,
    model_provider="openai",
)
print(f"✓ Agent ready with {len(agent.graph.nodes())} nodes in knowledge graph\n")

print("❓ Asking: 'What COBOL programs are in the CUSTOMER domain?'\n")
response = agent.analyze("What COBOL programs are in the CUSTOMER domain?")

print(f"✨ Response:\n{response}\n")
