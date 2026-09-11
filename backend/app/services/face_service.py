from typing import Dict, Any, List
import logging
import math

logger = logging.getLogger("trustscan_audit")

# Strict threshold for strict verification (0.6 is default for dlib/face_recognition, lower is stricter)
MATCH_THRESHOLD = 0.6 

def euclidean_distance(vector1: List[float], vector2: List[float]) -> float:
    """Calculates the Euclidean distance between two embeddings."""
    return math.sqrt(sum((v1 - v2) ** 2 for v1, v2 in zip(vector1, vector2)))

def verify_faces(doc_image_path: str, live_image_path: str) -> Dict[str, Any]:
    """
    Extracts faces from both images and compares their 128-d embeddings.
    """
    try:
        import face_recognition
    except ImportError:
        logger.error("face_recognition library not found. Falling back to UNAVAILABLE.")
        return {
            "face_status": "FACE_ANALYSIS_UNAVAILABLE",
            "similarity_score": 0.0,  # Fail closed
            "error": "Face recognition dependency missing (dlib/face_recognition)"
        }

    try:
        # Load images into numpy arrays (RGB)
        doc_image = face_recognition.load_image_file(doc_image_path)
        live_image = face_recognition.load_image_file(live_image_path)
    except Exception as e:
        return {
            "face_status": "INVALID_IMAGE",
            "similarity_score": 0.0,
            "error": f"Failed to decode image files: {str(e)}"
        }

    try:
        # Detect bounding boxes (using HOG model for CPU efficiency)
        doc_face_locations = face_recognition.face_locations(doc_image, model="hog")
        live_face_locations = face_recognition.face_locations(live_image, model="hog")
        
        # Validation checks for exact face counts
        if len(doc_face_locations) == 0 or len(live_face_locations) == 0:
            return {
                "face_status": "FACE_NOT_FOUND",
                "similarity_score": 0.0,
                "error": "No face detected in one or both images."
            }
            
        if len(doc_face_locations) > 1 or len(live_face_locations) > 1:
            return {
                "face_status": "FACE_INCONCLUSIVE",
                "similarity_score": 0.0,
                "error": "Multiple faces detected. Verification aborted."
            }
            
        # Extract 128-dimensional facial embeddings
        doc_encodings = face_recognition.face_encodings(doc_image, known_face_locations=doc_face_locations)
        live_encodings = face_recognition.face_encodings(live_image, known_face_locations=live_face_locations)
        
        if not doc_encodings or not live_encodings:
             return {
                "face_status": "FACE_NOT_FOUND",
                "similarity_score": 0.0,
                "error": "Failed to extract facial landmarks."
            }
            
        doc_vector = doc_encodings[0]
        live_vector = live_encodings[0]
        
        # Calculate strict Euclidean distance
        distance = euclidean_distance(doc_vector, live_vector)
        
        # Convert distance to a similarity score between 0.0 and 1.0
        # If distance is exactly threshold (0.6), score is 0.5. 
        # If distance is 0 (identical), score is 1.0
        # A standard mathematical normalization approach:
        similarity_score = max(0.0, 1.0 - (distance / (MATCH_THRESHOLD * 2)))
        
        if distance <= MATCH_THRESHOLD:
            status = "FACE_MATCH"
            # Hardcap minimum similarity for a match to ensure it beats the risk thresholds
            similarity_score = max(similarity_score, 0.75) 
        else:
            status = "FACE_NO_MATCH"
            
        return {
            "face_status": status,
            "similarity_score": similarity_score,
            "distance_metric": distance
        }
        
    except Exception as e:
        logger.error(f"Face Verification Fatal Error: {str(e)}")
        return {
            "face_status": "FACE_ANALYSIS_UNAVAILABLE",
            "similarity_score": 0.0,
            "error": str(e)
        }
