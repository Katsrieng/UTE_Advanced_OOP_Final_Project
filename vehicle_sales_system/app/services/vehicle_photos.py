"""Local vehicle photos: validate bytes, save a relative path, then clean old files."""
from io import BytesIO
import logging
from pathlib import Path
import re
from uuid import uuid4
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename


class PhotoError(ValueError):
    """An upload problem that can be safely displayed in the vehicle form."""


class VehiclePhotoService:
    FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
    UPLOAD_PATTERN = re.compile(r'uploads/vehicles/vehicle_[0-9a-f]{32}\.(jpg|jpeg|png|webp)\Z')
    MAX_PIXELS = 20_000_000

    def __init__(self, repository, static_folder, max_bytes=5 * 1024 * 1024):
        self.repository = repository
        self.static_folder = Path(static_folder).resolve()
        self.upload_folder = self.static_folder / 'uploads' / 'vehicles'
        self.max_bytes = max_bytes

    def upload_path(self, image):
        """Accept only our generated names, never client-supplied filesystem paths."""
        if not isinstance(image, str) or not self.UPLOAD_PATTERN.fullmatch(image):
            return None
        folder = self.upload_folder.resolve()
        path = (self.static_folder / image).resolve()
        if not folder.is_relative_to(self.static_folder) or path.parent != folder:
            return None
        if (self.static_folder / image).is_symlink():
            return None
        return path

    def image_path(self, vehicle):
        image = (vehicle or {}).get('image', '')
        path = self.upload_path(image)
        if path and path.is_file():
            return image
        if image in ('sedan.svg', 'suv.svg'):
            return 'images/vehicles/' + image
        return 'images/vehicles/sedan.svg'

    def has_photo(self, vehicle):
        return self.image_path(vehicle).startswith('uploads/vehicles/')

    def save_upload(self, upload):
        extension = Path(secure_filename(upload.filename or '')).suffix.lower()
        if extension not in self.FORMATS:
            raise PhotoError('Choose a JPG, JPEG, PNG or WebP vehicle photo.')
        data = upload.stream.read(self.max_bytes + 1)
        if len(data) > self.max_bytes:
            raise PhotoError('The photo is too large. Choose an image no larger than 5 MB.')
        image = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as source:
                    if source.format != self.FORMATS[extension]:
                        raise PhotoError('The photo content does not match its file extension.')
                    if source.width * source.height > self.MAX_PIXELS:
                        raise PhotoError('Choose a photo with no more than 20 million pixels.')
                    if getattr(source, 'n_frames', 1) != 1:
                        raise PhotoError('Choose a still vehicle photo rather than an animated image.')
                    source.verify()
                with Image.open(BytesIO(data)) as source:
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    image = oriented.convert('RGB' if extension in ('.jpg', '.jpeg') else 'RGBA')
                    oriented.close()
            image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            # Re-encode pixels only: no EXIF, trailing payload, or original filename.
            image.info.clear()
            relative = f'uploads/vehicles/vehicle_{uuid4().hex}{extension}'
            path = self.upload_path(relative)
            if path is None:
                raise PhotoError('Photo storage is unavailable. Please contact the administrator.')
            self.upload_folder.mkdir(parents=True, exist_ok=True)
            created = False
            try:
                with path.open('xb') as destination:
                    created = True
                    image.save(destination, format=self.FORMATS[extension])
            except Exception:
                if created:
                    self.remove_unreferenced(relative)
                raise
            return relative
        except PhotoError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise PhotoError('The photo could not be read or saved. Choose a valid JPG, PNG or WebP image and try again.') from exc
        finally:
            if image is not None:
                image.close()

    def remove_unreferenced(self, image):
        path = self.upload_path(image)
        if path is None:
            return
        try:
            if self.repository.image_referenced(image):
                return
        except Exception:
            logging.getLogger(__name__).warning('Photo cleanup postponed because reference lookup failed.')
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logging.getLogger(__name__).warning('Could not clean an unreferenced vehicle photo: %s', image)

    def save_vehicle(self, values, item_id=None, upload=None, remove=False):
        """The database commit completes before any old photo is removed."""
        values = dict(values)
        new_image = self.save_upload(upload) if upload is not None and upload.filename else None
        old_image = 'sedan.svg'
        try:
            with self.repository.transaction():
                original = self.repository.get('vehicles', item_id, lock=True) if item_id else None
                if item_id and not original:
                    raise ValueError('Vehicle not found.')
                old_image = original.get('image', 'sedan.svg') if original else 'sedan.svg'
                if original and original['status'] == 'SOLD':
                    protected = ('code', 'vin', 'brand', 'model', 'year', 'price', 'status')
                    if any(key in values and values[key] != original[key] for key in protected):
                        raise ValueError('Sold vehicle identity and price are preserved for invoice history.')
                if not original and values.get('status') == 'SOLD':
                    raise ValueError('Sold status is assigned by completing a sale.')
                values['image'] = new_image or ('sedan.svg' if remove else old_image)
                row = self.repository.save('vehicles', values, item_id)
        except Exception as exc:
            if new_image:
                self.remove_unreferenced(new_image)
            # Never expose raw database errors to the vehicle form.
            from app.database import PersistenceError
            message = str(exc) if isinstance(exc, (PersistenceError, ValueError)) else 'The vehicle could not be saved. Your previous photo has been kept. Please try again.'
            raise PhotoError(message) from exc
        if values['image'] != old_image:
            self.remove_unreferenced(old_image)
        return row
