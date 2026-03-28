import pygame, threading, time

def stop_music():
    pygame.mixer.music.stop()

def play_music(mp3File):
    pygame.mixer.init()
    pygame.mixer.music.load(mp3File)
    pygame.mixer.music.play()