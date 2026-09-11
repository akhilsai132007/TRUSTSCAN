import io
from typing import Dict, Any, List
import logging

logger = logging.getLogger("trustscan_audit")

def analyze_image(image_path: str) -> Dict[str, Any]:
    """
    Performs Error Level Analysis (ELA) to detect image tampering.
    """
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return {
            "tampering_status": "ANALYSIS_UNAVAILABLE",
            "tampering_score": 1.0, # Fail-closed
            "method_used": "Error Level Analysis (ELA)",
            "suspicious_regions": [],
            "error": "PIL dependency missing"
        }
        
    try:
        # 1. Open original image
        original = Image.open(image_path).convert('RGB')
        
        # 2. Re-compress the image to a known quality
        quality = 90
        compressed_io = io.BytesIO()
        original.save(compressed_io, 'JPEG', quality=quality)
        compressed_io.seek(0)
        compressed = Image.open(compressed_io)
        
        # 3. Calculate absolute difference
        diff = ImageChops.difference(original, compressed)
        
        # 4. We use the raw difference image to calculate absolute variance.
        # Dynamically scaling it artificially inflates noise in perfectly clean images.
        ela_img = diff
        
        # 5. Grid analysis for suspicious regions
        width, height = original.size
        grid_cols = 10
        grid_rows = 10
        
        block_w = width // grid_cols
        block_h = height // grid_rows
        
        blocks = []
        max_block_variance = 0.0
        
        # To avoid false positives from natural edges, we look for extreme isolated variances
        for row in range(grid_rows):
            for col in range(grid_cols):
                left = col * block_w
                upper = row * block_h
                right = left + block_w
                lower = upper + block_h
                
                box = (left, upper, right, lower)
                region = ela_img.crop(box)
                stat = ImageStat.Stat(region)
                
                # Use the max standard deviation across RGB channels as the variance indicator
                variance = max(stat.stddev) / 255.0 
                
                if variance > max_block_variance:
                    max_block_variance = variance
                    
                blocks.append({
                    "col": col,
                    "row": row,
                    "box": {"left": left, "upper": upper, "right": right, "lower": lower},
                    "variance": variance
                })
                
        # 6. Interpret Results
        # Normalize score (0.0 to 1.0). In a real production system this threshold is tuned via ML
        # For our baseline, variance > 0.01 is highly suspicious for a JPEG
        tampering_score = min(max_block_variance * 50.0, 1.0) 
        
        status = "TAMPERING_DETECTED" if tampering_score >= 0.4 else "NO_TAMPERING_INDICATOR"
        
        # Only return the most suspicious regions (top 5%)
        suspicious_regions = []
        if status == "TAMPERING_DETECTED":
            sorted_blocks = sorted(blocks, key=lambda x: x["variance"], reverse=True)
            suspicious_regions = sorted_blocks[:3] # Top 3 most manipulated blocks
            
        return {
            "tampering_status": status,
            "tampering_score": tampering_score,
            "method_used": "Error Level Analysis (ELA)",
            "suspicious_regions": suspicious_regions
        }
        
    except IOError:
        return {
            "tampering_status": "INVALID_IMAGE",
            "tampering_score": 1.0, # Fail-closed
            "method_used": "Error Level Analysis (ELA)",
            "suspicious_regions": [],
            "error": "Cannot decode image file"
        }
    except Exception as e:
        logger.error(f"ELA Processing Error: {str(e)}")
        return {
            "tampering_status": "ANALYSIS_UNAVAILABLE",
            "tampering_score": 1.0,
            "method_used": "Error Level Analysis (ELA)",
            "suspicious_regions": [],
            "error": str(e)
        }
