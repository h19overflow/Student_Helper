"""Generate and save AWS VPC networking diagrams using Google Gemini Nanobanana API."""

from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize client
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=api_key)

# Generate image
try:
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents="Create a detailed diagram illustrating AWS VPC networking architecture for enhanced understanding. Show: VPC boundaries, public and private subnets in multiple availability zones, NAT gateway, Internet Gateway, route tables, security groups, and NLB (Network Load Balancer). Use color coding and labels for clarity.",
    )

    # Extract and save image
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                image_data = part.inline_data

                # Save image to file
                mime_type = image_data.mime_type if hasattr(image_data, 'mime_type') else 'image/png'
                file_ext = mime_type.split('/')[-1]
                output_path = f"aws_vpc_diagram.{file_ext}"

                with open(output_path, 'wb') as f:
                    f.write(image_data.data)

                print(f"✓ Image saved: {output_path}")
                print(f"✓ Size: {len(image_data.data)} bytes")
                print(f"✓ Type: {mime_type}")

except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
