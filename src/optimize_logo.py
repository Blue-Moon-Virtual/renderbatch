from PIL import Image
import os
from pathlib import Path

def optimize_logo(input_path, output_path, target_size):
    """Optimize a logo image with proper resampling and compression."""
    with Image.open(input_path) as img:
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Resize with high-quality resampling
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Save with optimized compression
        img.save(
            output_path,
            'PNG',
            optimize=True,
            quality=95
        )

def main():
    # Get the base path
    base_path = Path(__file__).parent.parent
    assets_path = base_path / 'assets'
    
    # Define target sizes
    sizes = {
        'small': (64, 64),
        'medium': (128, 128),
        'large': (256, 256),
        'xlarge': (512, 512)
    }
    
    # Create optimized versions
    for size_name, size in sizes.items():
        output_path = assets_path / f'logo_optimized_{size_name}.png'
        optimize_logo(
            assets_path / 'logo_char.png',
            output_path,
            size
        )
        print(f"Created {size_name} version: {output_path}")

if __name__ == '__main__':
    main() 