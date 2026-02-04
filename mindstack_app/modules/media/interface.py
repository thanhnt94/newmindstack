# File: mindstack_app/modules/media/interface.py
"""
Media Interface
================
Public API for other modules to interact with media functionality.
All cross-module media operations must go through this interface.
"""

from typing import Optional, Iterable
from .services.image_service import ImageService
from .schemas import MediaResponseDTO


class MediaInterface:
    """Public interface for media module operations."""
    
    @staticmethod
    def search_and_cache_image(
        text: str, 
        max_results: int = 8
    ) -> MediaResponseDTO:
        """
        Search for an image and cache it locally.
        
        Args:
            text: Search query text
            max_results: Maximum number of search results to try
            
        Returns:
            MediaResponseDTO with file path or error
        """
        service = ImageService()
        absolute_path, success, message = service.get_cached_or_download_image(
            text, 
            max_results=max_results
        )
        
        if success and absolute_path:
            relative_path = service._to_relative_cache_path(absolute_path)
            return MediaResponseDTO(
                status='success',
                file_path=absolute_path,
                relative_path=relative_path
            )
        
        return MediaResponseDTO(
            status='error',
            error=message
        )
    
    @staticmethod
    async def batch_generate_images(
        task, 
        container_ids: Optional[Iterable[int]] = None
    ) -> None:
        """
        Generate images for items missing images in specified containers.
        
        Args:
            task: Background task object for progress tracking
            container_ids: Optional list of container IDs to process
        """
        service = ImageService()
        await service.generate_images_for_missing_cards(task, container_ids)
    
    @staticmethod
    def clean_orphan_cache(task) -> None:
        """
        Remove cached images that are no longer referenced.
        
        Args:
            task: Background task object for progress tracking
        """
        service = ImageService()
        service.clean_orphan_image_cache(task)
    
    @staticmethod
    def convert_to_relative_path(absolute_path: str) -> Optional[str]:
        """Convert absolute path to relative path for URL generation."""
        service = ImageService()
        return service._to_relative_cache_path(absolute_path)
