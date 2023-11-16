from abc import ABC, abstractmethod # Used  to declare abstract class and pure virtual functions
from PyQt5 import QtCore, QtGui
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QFileDialog
import numpy as np
import bisect
import librosa
from scipy.signal.windows import get_window
from scipy.signal.windows import boxcar
import math


class BaseMode(ABC):
    def __init__(self, ui, input_time_graph, output_time_graph, frequency_graph, input_spectro, output_spectro, slider1, slider2, slider3, slider4):
        self.ui = ui
        self.input_graph = input_time_graph
        self.output_graph = output_time_graph
        self.frequency_graph = frequency_graph
        self.input_spectrogram = input_spectro
        self.output_spectrogram = output_spectro
        self.time_domain_X_coordinates = []
        self.time_domain_Y_coordinates = []
        self.slider1 = slider1
        self.slider2 = slider2
        self.slider3 = slider3
        self.slider4 = slider4

        self.X_Points_Plotted = 0
        self.paused = False
        self.speed = 10
        self.stopped = False
        self.player = QMediaPlayer()

    @abstractmethod
    def modify_frequency(self, value: int):
        pass
    
    def load_signal(self):
        self.input_graph.clear()
        File_Path, _ = QFileDialog.getOpenFileName(None, "Browse Signal", "", "All Files (*)")
        
        self.audio_data, self.sample_rate = librosa.load(File_Path)

        self.time_domain_X_coordinates = np.arange(len(self.audio_data)) / self.sample_rate
        self.time_domain_Y_coordinates = self.audio_data
        
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(File_Path)))
        self.stopped = False
        self.plot_signal()
           
    def plot_signal(self):
        self.input_graph.setLimits(xMin=0, xMax=float('inf'))
        self.data_line = self.input_graph.plot(self.time_domain_X_coordinates[:1], self.time_domain_Y_coordinates[:1],pen="g")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()
        self.player.play()
        self.plot_frequency_domain()

    def update_plot_data(self):
        if not self.paused and not self.stopped:             
            sound_position = self.player.position()
            sound_duration = self.player.duration()
            progress = sound_position / sound_duration

            if progress == 1:
                self.stopped = True

            target_x = int(progress * max(self.time_domain_X_coordinates))
            target_index = bisect.bisect_left(self.time_domain_X_coordinates, target_x)

            self.input_graph.getViewBox().setXRange(target_x - 4, target_x)
            self.data_line.setData(self.time_domain_X_coordinates[:target_index], self.time_domain_Y_coordinates[:target_index])

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.player.pause()
        else:
            if not self.stopped:
                self.player.play()

    def reset(self):
        self.stopped = False
        self.player.stop()
        self.player.setPosition(0)
        self.player.play()

    def update_speed(self,slider):
        self.player.setPlaybackRate(slider.value())

    def stop(self):
        self.player.stop()
        self.stopped = True
        self.input_graph.clear()
        self.input_graph.getViewBox().setXRange(0,4)

    def zoomin(self):
        self.input_graph.getViewBox().scaleBy((0.9, 0.9))

    def zoomout(self):
        self.input_graph.getViewBox().scaleBy((1.1,1.1))

    def smoothing_window(self):
        # Check which radio button is selected
        if self.ui.Smoothing_Window_Hamming_Radio_Button.isChecked():
            # Generate Hamming window
            hamming_window = get_window('hamming', self.ui.Smoothing_Window_Frequency_Slider.value())
            # Scale the Hamming window to the desired amplitude
            scaled_hamming_window = self.ui.Smoothing_Window_Amplitude_Slider.value() * hamming_window / np.max(hamming_window)
            return (scaled_hamming_window)

        elif self.ui.Smoothing_Window_Hanning_Radio_Button.isChecked():
            # Generate Hanning window
            hanning_window = get_window('hann', self.ui.Smoothing_Window_Frequency_Slider.value())
            # Scale the Hanning window to the desired amplitude
            scaled_hanning_window = self.ui.Smoothing_Window_Amplitude_Slider.value() * hanning_window / np.max(hanning_window)
            return (scaled_hanning_window)

        elif self.ui.Smoothing_Window_Rectangle_Radio_Button.isChecked():
            # generate and adjust the height as desired
            rectangle_window = boxcar(self.ui.Smoothing_Window_Frequency_Slider.value()) * self.ui.Smoothing_Window_Amplitude_Slider.value()
            return (rectangle_window)

        elif self.ui.Smoothing_Window_Gaussian_Radio_Button.isChecked():
            std_dev = self.ui.Smoothing_Window_Frequency_Slider.value() / (2 * math.sqrt(2 * math.log(2)))
            gaussian_window = get_window(('gaussian', std_dev), self.ui.Smoothing_Window_Frequency_Slider.value()) * self.ui.Smoothing_Window_Amplitude_Slider.value()
            return (gaussian_window)

    def plot_smoothing(self):
        self.current_smoothing = self.smoothing_window()
        self.ui.Smoothing_Window_PlotWidget.clear()
        self.ui.Smoothing_Window_PlotWidget.plot(self.current_smoothing)

    def plot_frequency_domain(self):
        # fft_result = np.fft.fft(signal)
        # frequencies = np.fft.fftfreq(len(fft_result), 1/sampling_rate)
        # self.freq_graph.plot.plot(frequencies, np.abs(fft_result))
        signal = np.array(self.time_domain_Y_coordinates)
        dt = self.time_domain_X_coordinates[1] - self.time_domain_X_coordinates[0]
        # if dt is None:
        #     dt = 1
        #     t = np.arange(0, signal.shape[-1])
        # else: #mosta7el teb2a b none f m4 needed awy, arga3laha ba3den
        t = np.arange(0, signal.shape[-1]) * dt

        if signal.shape[0] % 2 != 0:
            t = t[0:-1]
            signal = signal[0:-1]

        fft_result = np.fft.fft(signal) / t.shape[0]  # Divided by size t for coherent magnitude
        freq = np.fft.fftfreq(t.shape[0], d=dt)

        # Plot analytic signal - right half of the frequency axis is needed only...
        first_neg_index = np.argmax(freq < 0)
        freq_axis_pos = freq[0:first_neg_index]
        sig_fft_pos = 2 * fft_result[0:first_neg_index]  # *2 because of the magnitude of the analytic signal
        self.frequency_graph.plot(freq_axis_pos, np.abs(sig_fft_pos))
  