"""Generate website images using Gemini 3 Pro native image generation."""

import asyncio
import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import httpx

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = "gemini-3-pro-image-preview"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "images")

# Image prompts: (filename, prompt)
IMAGE_PROMPTS = [
    (
        "hero-brain-network.png",
        "A hyper-realistic 3D render of a glowing digital brain floating in dark space. "
        "The brain is constructed from thousands of tiny luminous nodes connected by "
        "thin glowing filaments in electric purple and blue. Some clusters of nodes "
        "pulse brighter, representing active knowledge. Volumetric light rays emanate "
        "from the core. Deep dark navy-black background. Cinematic lighting, 8K quality, "
        "ultra-detailed. No text, no labels, no watermarks. Widescreen 16:9 composition."
    ),
    (
        "problem-amnesia.png",
        "A striking conceptual 3D illustration: a translucent holographic chat bubble "
        "shattering into glass-like fragments and dissolving into particles. The fragments "
        "drift away into darkness. Nearby, an identical fresh chat bubble appears, "
        "representing the same wrong answer repeating. Color palette: shattered pieces "
        "in warm red-orange, new bubble in cold blue. Dark navy-black background. "
        "Cinematic, moody lighting. No text, no labels, no watermarks. 16:9 composition."
    ),
    (
        "architecture-memory.png",
        "An elegant 3D isometric visualization of four distinct data layers stacked "
        "vertically with glowing connections between them. Top layer: a crackling "
        "red-orange energy field (active memory). Second: a beautiful blue network "
        "of interconnected spheres (graph memory). Third: flowing purple waves of "
        "data points (vector memory). Bottom: a solid green crystalline structure "
        "(audit layer). Translucent data streams flow between all layers. Dark "
        "navy-black background. Clean, premium tech aesthetic. No text, no labels. 16:9."
    ),
    (
        "feature-correction.png",
        "A 3D render showing a glowing knowledge node (sphere) transitioning from "
        "red to green. The red version is connected by a dotted golden arrow labeled-free "
        "arc to a bright green updated version. A subtle version-history trail of "
        "faded ghost spheres behind the red one shows previous states. A small "
        "human silhouette icon floats nearby. Dark background, clean minimal style. "
        "No text, no labels, no watermarks. Square 1:1 composition."
    ),
    (
        "feature-activation.png",
        "A stunning top-down view of a knowledge graph network. One central node "
        "emits a bright purple energy pulse that ripples outward like a shockwave. "
        "Nodes closest to the center glow brilliant white-purple (highly activated). "
        "Nodes further away glow dimmer blue. Nodes at the edges are nearly dark grey "
        "(below threshold, not selected). The ripple effect creates beautiful concentric "
        "rings of light. Dark space background. No text, no labels. Square 1:1."
    ),
    (
        "feature-confidence.png",
        "Three floating holographic cards arranged in a slight cascade. The top card "
        "has a bright green glowing border and a shield icon (high confidence). The "
        "middle card has an amber-yellow glowing border with a caution icon (medium). "
        "The bottom card has a red glowing border with a question mark icon (low). "
        "Each card emits soft light matching its color. Dark background, sleek UI "
        "aesthetic. No text, no labels, no watermarks. Square 1:1."
    ),
    (
        "feature-audit.png",
        "A beautiful 3D timeline visualization: a vertical glowing line with "
        "branching nodes at intervals. Each node is a small glowing orb connected "
        "to a translucent data card. Older nodes at the bottom are dimmer teal, "
        "newer ones at the top are brighter emerald green. Small user avatar "
        "silhouettes float beside some nodes. The timeline has a sense of depth "
        "and perspective. Dark background. No text, no labels. Square 1:1."
    ),
    (
        "usecase-devops.png",
        "A futuristic command center scene: multiple holographic screens floating "
        "in dark space showing a knowledge graph, server metrics, and an AI chat "
        "interface. Blue and purple accent lighting. A subtle silhouette of an "
        "engineer interacting with the holographic displays. Server rack outlines "
        "glow softly in the background. Cinematic, cyberpunk-lite aesthetic. "
        "No text, no labels, no watermarks. 4:3 composition."
    ),
    (
        "comparison-rag-vs-cortex.png",
        "A split-screen 3D illustration. Left half: a chaotic mess of hundreds of "
        "documents being crammed into a tiny glowing funnel, overflowing and "
        "spilling — colored in dull reds and grays (representing wasteful RAG). "
        "Right half: a precise laser beam from a lens elegantly selecting 5-6 "
        "bright glowing nodes from a clean organized graph network — colored in "
        "vibrant purple and green (representing smart selection). Clear visual "
        "contrast. Dark background. No text, no labels. 16:9."
    ),
    (
        "cta-brain-glow.png",
        "A majestic glowing digital brain made of interconnected light nodes, "
        "viewed from slightly below looking up. One node near the center has a "
        "brilliant starburst of light — a correction being applied — and the "
        "light ripples outward through the network, making the entire brain "
        "glow brighter. Purple, blue, and white color palette. Volumetric god "
        "rays emanating upward. Cinematic, awe-inspiring, hero-quality. Dark "
        "background. No text, no watermarks. 16:9."
    ),
    (
        "mcp-integration.png",
        "A sleek 3D render of a terminal/CLI window floating in dark space, "
        "connected by glowing data streams to a central brain-like knowledge "
        "graph. Multiple terminal windows at different angles all connect to "
        "the same central brain — representing multiple CLI tools (Claude Code, "
        "Codex, etc.) all accessing the same knowledge. Neon purple and blue "
        "accent lines. Futuristic, clean. No text, no labels. 16:9."
    ),
    (
        "api-endpoints.png",
        "A beautiful 3D visualization of API architecture: a central glowing "
        "server hexagon with multiple colored connection lines radiating outward "
        "to different app icons (mobile, web, chat, terminal). Each connection "
        "line pulses with data flowing in both directions. The server hexagon "
        "has a subtle brain/network pattern inside it. Blue, purple, and teal "
        "color palette. Dark background. No text, no labels. 16:9."
    ),
    (
        "brain-inspiration.png",
        "A breathtaking split-composition 3D render. Left half shows a detailed "
        "anatomical human brain with visible neural pathways glowing in warm amber "
        "and terracotta tones — synapses firing with tiny sparks of light along "
        "dendrites, the hippocampus subtly highlighted with a brighter glow. "
        "Right half shows a digital mirror: a futuristic AI knowledge graph made "
        "of luminous nodes and edges in matching warm amber-terracotta colors, "
        "structurally mirroring the brain's neural layout. A seamless morphing "
        "transition zone in the center where biological neurons blend into "
        "digital nodes. Volumetric warm light. Dark charcoal-black background. "
        "Scientific yet artistic. Cinematic, 8K quality. No text, no labels, "
        "no watermarks. Widescreen 16:9 composition."
    ),
]


async def generate_image(filename: str, prompt: str) -> bool:
    """Generate a single image using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        print("ERROR: No GEMINI_API_KEY or LLM_API_KEY found")
        return False

    url = f"{GEMINI_API_BASE}/{MODEL}:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            print(f"  Generating {filename}...", end=" ", flush=True)
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            print("FAILED (no candidates)")
            return False

        parts = candidates[0].get("content", {}).get("parts", [])

        for part in parts:
            if "inlineData" in part:
                inline_data = part["inlineData"]
                if inline_data.get("data"):
                    img_bytes = base64.b64decode(inline_data["data"])
                    with open(filepath, "wb") as f:
                        f.write(img_bytes)
                    size_kb = len(img_bytes) / 1024
                    print(f"OK ({size_kb:.0f} KB)")
                    return True

        print("FAILED (no image in response)")
        return False

    except httpx.HTTPStatusError as e:
        print(f"FAILED (HTTP {e.response.status_code}: {e.response.text[:300]})")
        return False
    except Exception as e:
        print(f"FAILED ({e})")
        return False


async def main():
    print(f"Generating {len(IMAGE_PROMPTS)} images with {MODEL}...")
    print(f"Output: {OUTPUT_DIR}\n")

    results = []
    for filename, prompt in IMAGE_PROMPTS:
        ok = await generate_image(filename, prompt)
        results.append((filename, ok))
        # Delay to avoid rate limiting
        await asyncio.sleep(3)

    print(f"\n--- Results ---")
    success = sum(1 for _, ok in results if ok)
    print(f"Generated: {success}/{len(results)}")
    for filename, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {filename}")


if __name__ == "__main__":
    asyncio.run(main())
