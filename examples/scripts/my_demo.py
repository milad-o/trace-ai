"""Quick TraceAI demo that loads COBOL samples and runs a question."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from traceai.agents import TraceAI


async def run_demo() -> None:
	"""Load COBOL programs and ask TraceAI a question."""
	# Ensure API keys and other env vars are available to TraceAI.
	load_dotenv(Path.cwd() / ".env")

	agent = TraceAI(model_provider="openai")

	cobol_dir = Path(__file__).parent.parent / "inputs/cobol"
	try:
		await agent.load_documents(cobol_dir, pattern="*.cbl")
	except TypeError as exc:
		if "create_deep_agent" in str(exc):
			print(
				"⚠️  DeepAgents API mismatch. Update TraceAI._create_agent_async() "
				"to match the latest create_deep_agent signature."
			)
			return
		raise

	response = await agent.query(
		"List the COBOL programs available in the sample dataset and summarize their purpose."
	)

	print("\n=== Agent Response ===\n")
	print(response)


def main() -> None:
	asyncio.run(run_demo())


if __name__ == "__main__":
	main()

