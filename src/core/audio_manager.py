import os
import sys
import threading

import pygame

class AudioManager:
    _instance = None
    
    CHANNEL_HIGH = 0
    CHANNEL_NORMAL = 1
    CHANNEL_SFX = 2

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.sounds = {}
        self._sound_lock = threading.RLock()
        self._preload_thread = None
        self._preload_started = False
        self._preload_complete = False

        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            self._initialized = True
            self.preload_all_async()
            print("Audio Manager initialized successfully.")
        except pygame.error as e:
            print(f"Failed to initialize pygame mixer: {e}")
            self._initialized = False

    def _assets_dir(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            if not os.path.exists(os.path.join(base_dir, 'assets')) and os.path.exists(os.path.join(base_dir, '_internal', 'assets')):
                base_dir = os.path.join(base_dir, '_internal')
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, 'assets')

    def _normalize_key(self, filename):
        base, ext = os.path.splitext(filename)
        return base + ext.lower()

    def _store_sound(self, key_path, sound):
        self.sounds[key_path] = sound
        basename = os.path.basename(key_path)
        if basename not in self.sounds:
            self.sounds[basename] = sound

    def _load_sound_file(self, assets_dir, full_path):
        sound = pygame.mixer.Sound(full_path)
        rel_path = os.path.relpath(full_path, assets_dir).replace('\\', '/')
        key_path = self._normalize_key(rel_path)
        with self._sound_lock:
            self._store_sound(key_path, sound)
        return key_path, sound

    def _load_assets(self):
        """Preloads all .wav and .mp3 files from the assets directory recursively."""
        assets_dir = self._assets_dir()

        if not os.path.exists(assets_dir):
            print(f"Assets directory not found: {assets_dir}")
            return

        for root, dirs, files in os.walk(assets_dir):
            for filename in files:
                if not filename.lower().endswith(('.wav', '.mp3')):
                    continue
                full_path = os.path.join(root, filename)
                try:
                    key_path, _ = self._load_sound_file(assets_dir, full_path)
                    print(f"Loaded sound: {key_path}")
                except pygame.error as e:
                    print(f"Failed to load sound {full_path}: {e}")

    def preload_all_async(self):
        if not self._initialized or self._preload_started:
            return

        self._preload_started = True

        def _worker():
            try:
                self._load_assets()
            finally:
                self._preload_complete = True

        self._preload_thread = threading.Thread(target=_worker, name='AudioPreload', daemon=True)
        self._preload_thread.start()

    def _get_sound(self, filename):
        filename = self._normalize_key(filename)
        with self._sound_lock:
            sound = self.sounds.get(filename)
            if sound is not None:
                return sound

        assets_dir = self._assets_dir()
        full_path = os.path.join(assets_dir, filename.replace('/', os.sep))
        if not os.path.exists(full_path):
            basename_path = os.path.join(assets_dir, os.path.basename(filename))
            if os.path.exists(basename_path):
                full_path = basename_path
            else:
                return None

        try:
            _, sound = self._load_sound_file(assets_dir, full_path)
            print(f"Loaded sound on demand: {filename}")
            return sound
        except pygame.error as e:
            print(f"Failed to load sound {full_path}: {e}")
            return None

    def _get_channel(self, channel_id):
        """Returns the pygame Channel object."""
        if not self._initialized:
            return None
        return pygame.mixer.Channel(channel_id)

    def play(self, filename, channel_type):
        """
        Plays a sound on the specified channel type.
        
        Args:
            filename (str): The name of the .wav file (e.g., "alert.wav").
            channel_type (int): One of CHANNEL_HIGH, CHANNEL_NORMAL, CHANNEL_SFX.
        """
        if not self._initialized:
            return

        sound = self._get_sound(filename)
        if sound is None:
            filename = self._normalize_key(filename)
            print(f"Sound not found: {filename}")
            return

        try:
            channel = self._get_channel(channel_type)
            if channel is None:
                sound.play()
                return

            # Each notification class owns a stable mixer channel. A new
            # high-priority notification replaces the previous high-priority
            # one instead of being dropped when all auto channels are busy.
            channel.play(sound)
        except pygame.error as e:
            print(f"Error playing sound {filename}: {e}")

    def stop_all(self):
        """Stops all playback on all channels."""
        if self._initialized:
            pygame.mixer.stop()
