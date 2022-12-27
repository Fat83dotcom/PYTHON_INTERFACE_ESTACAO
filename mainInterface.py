import sys
import serial
import os
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QMutex, pyqtSlot
from interface import Ui_MainWindow
from serial import Serial
from confidentials import define_arquivo
import time
import csv
import matplotlib.pyplot as plt
import matplotlib.backends.backend_pdf
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from confidentials import meu_email, minha_senha, my_recipients
from statistics import mean
from string import Template
from itertools import count
from math import nan


class EmailWorker(QObject):
    termino = pyqtSignal()
    msgEnvio = pyqtSignal(str)

    def __init__(self, inicio, umi, press, t1, t2, t1max,
                 t1min, t2max, t2min, umimax, umimini,
                 pressmax, pressmini, ini, fim, path, parent=None):
        super().__init__(parent)
        self.inicio = inicio
        self.path = path
        self.umi = umi
        self.press = press
        self.t1 = t1
        self.t2 = t2
        self.t1max = t1max
        self.t1min = t1min
        self.t2max = t2max
        self.t2min = t2min
        self.umimax = umimax
        self.umimini = umimini
        self.pressmax = pressmax
        self.pressmini = pressmini
        self.ini = ini
        self.fim = fim

    @staticmethod
    def __anexadorPdf(enderecoPdf, msg):
        with open(enderecoPdf, 'rb') as pdf:
            anexo = MIMEApplication(pdf.read(), _subtype='pdf')
            pdf.close()
            anexo.add_header('Conteudo', enderecoPdf)
            msg.attach(anexo)

    def run(self):
        msg = MIMEMultipart()
        msg['from'] = 'Fernando Mendes'
        msg['to'] = ','.join(my_recipients())
        msg['subject'] = f'Monitoramento Estação Metereologica Fat83dotcom {data()}'
        corpo = MIMEText(renderizadorHtml(self.umi, self.press, self.t1, self.t2,
                         self.t1max, self.t1min, self.t2max, self.t2min,
                         self.umimax, self.umimini, self.pressmax, self.pressmini,
                         self.ini, self.fim, data()), 'html')
        msg.attach(corpo)

        umidade = f'{self.path}/Umidade{self.inicio}.pdf'
        pressao = f'{self.path}/Pressao{self.inicio}.pdf'
        tmp1 = f'{self.path}/Temperatura_Interna{self.inicio}.pdf'
        temp2 = f'{self.path}/Temperatura_Externa{self.inicio}.pdf'

        self.__anexadorPdf(umidade, msg)
        self.__anexadorPdf(pressao, msg)
        self.__anexadorPdf(tmp1, msg)
        self.__anexadorPdf(temp2, msg)
        try:
            with smtplib.SMTP(host='smtp.gmail.com', port=587) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(''.join(meu_email()), ''.join(minha_senha()))
                smtp.send_message(msg)
                self.msgEnvio.emit('Email enviado com sucesso.')
        except Exception as e:
            self.msgEnvio.emit('Não foi possivel enviar o email.')
            self.msgEnvio.emit(f'Motivo: {e.__class__.__name__}: {e}')
        finally:
            os.remove(f'{self.path}/Umidade{self.inicio}.pdf')
            os.remove(f'{self.path}/Pressao{self.inicio}.pdf')
            os.remove(f'{self.path}/Temperatura_Interna{self.inicio}.pdf')
            os.remove(f'{self.path}/Temperatura_Externa{self.inicio}.pdf')
        self.termino.emit()


class TransSegundos:
    def __init__(self, horas) -> None:
        self.horas = horas

    def conversorHorasSegundo(self) -> int:
        horas = self.horas[:2]
        minutos = self.horas[3:]
        segundos = int(int(horas) * 3600 + int(minutos) * 60)
        return segundos


def leia_me():
    with open('LEIA_ME.txt', 'w') as file:
        texto = '''
                ***
                Para usar corretamente este programa, você deve observar os seguintes procedimentos:
                -> No arquivo "EMAIL_USER_DATA" é o local onde o usuário irá configurar seu login de
                email, respeitando algumas regras simples que, se não seguidas, podem ocasionar
                funcionamento inesperado, erros ou a quebra do programa.
                AS REGRAS SÃO:
                -> NA PRIMEIRA E SEGUNDA LINHA DO ARQUIVO, NOS CAMPOS "MEU EMAIL" E "MINHA SENHA", APÓS ":" COLOQUE UM (1) ESPAÇO E APENAS UM (1)
                ESPAÇO, E CASO ESSA REGRA NÃO SEJA SEGUIDA, O PROGRAMA NÃO LERÁ CORRETAMENTE OS DADOS E NÃO ENVIARÁ OS EMAILS CORRETAMENTE.
                -> NA TERCEIRA LINHA, INSIRA OS EMAILS DOS DESTINATARIOS, SEPARADOS POR VIRGULAS E SEM QUEBRAS DE LINHA.
                SE HOUVER QUEBRA DE LINHA, O PROGRAMA AINDA ENVIARÁ OS EMAILS MAS OCORRERÁ ERROS E OMISSÕES DE DADOS INDESEJADAS.
                -> SEGUINDO ESSAS REGRAS É ESPERADO QUE OS EMAILS SEJAM ENVIADOS SEM PROBLEMAS E, CASO ACONTEÇA ALGUM
                PROBLEMA, POR FAVOR, ENTRAR EM CONTATO COM O DESENVOLVEDOR EXPLICANDO O PROBLEMA.
                OBRIGADO!!!
                ***
        '''
        file.write(texto)


def renderizadorHtml(umidade, pressao, temp1, temp2, temp1max, temp1min,
                     temp2max, temp2min, umima, umimi, pressma, pressmi,
                     inicio, fim, data):
    with open('template.html', 'r') as doc:
        template = Template(doc.read())
        corpo_msg = template.safe_substitute(umi=umidade, press=pressao, t1=temp1, t2=temp2,
                                             t1max=temp1max, t1min=temp1min, t2max=temp2max,
                                             t2min=temp2min, umimax=umima, umimini=umimi,
                                             pressmax=pressma, pressmini=pressmi, ini=inicio,
                                             fim=fim, dat=data)
    return corpo_msg


def data() -> str:
    try:
        data = time.strftime('%d %b %Y %H:%M:%S', time.localtime())
        return data
    except (ValueError, Exception) as e:
        raise e


def dataDoArquivo() -> str:
    try:
        dataA = time.strftime('%b_%Y_log.csv').lower()
        return dataA
    except (ValueError, Exception) as e:
        raise e


def maximos(dados) -> float:
    try:
        return round(max(dados), 2)
    except (ValueError, Exception) as e:
        raise DadosError(f'{e.__class__.__name__} -> função: {maximos.__name__}: Não há dados a serem processados.')


def minimos(dados) -> float:
    try:
        return round(min(dados), 2)
    except (ValueError, Exception) as e:
        raise DadosError(f'{e.__class__.__name__} -> função: {minimos.__name__}: Não há dados a serem processados.')


def plot_umidade(uy, inicio, path):
    try:
        ux = range(len(uy))
        file = f'{path}/Umidade{inicio}.pdf'
        plt.title(f'Gráfico Umidade\n-> Inicio: {inicio} <-|-> Termino: {data()} <-\nMáxima: {maximos(uy)} --- Mínima: {minimos(uy)}')
        plt.xlabel('Tempo em segundos.')
        plt.ylabel('Umidade Relativa do Ar %')
        plt.plot(ux, uy)
        plt.savefig(file)
        plt.clf()
    except (ValueError, Exception) as e:
        raise e


def plot_pressao(py, inicio, path):
    try:
        px = range(len(py))
        file = f'{path}/Pressao{inicio}.pdf'
        plt.title(f'Gráfico Pressão\n-> Inicio: {inicio} <-|-> Termino: {data()} <-\nMáxima: {maximos(py)} --- Mínima: {minimos(py)}')
        plt.xlabel('Tempo em segundos.')
        plt.ylabel('Pressão Atmosferica em hPa')
        plt.plot(px, py)
        plt.savefig(file)
        plt.clf()
    except (ValueError, Exception) as e:
        raise e


def plot_temp1(t1y, inicio, path):
    try:
        t1x = range(len(t1y))
        file = f'{path}/Temperatura_Interna{inicio}.pdf'
        plt.title(f'Gráfico Temp Interna\n-> Inicio: {inicio} <-|-> Termino: {data()} <-\nMáxima: {maximos(t1y)} --- Mínima: {minimos(t1y)}')
        plt.xlabel('Tempo em segundos.')
        plt.ylabel('Temperatura em °C')
        plt.plot(t1x, t1y)
        plt.savefig(file)
        plt.clf()
    except (ValueError, Exception) as e:
        raise e


def plot_temp2(t2y, inicio, path):
    try:
        t2x = range(len(t2y))
        file = f'{path}/Temperatura_Externa{inicio}.pdf'
        plt.title(f'Gráfico Temp Externa\n-> Inicio: {inicio} <-|-> Termino: {data()} <-\nMáxima: {maximos(t2y)} --- Mínima: {minimos(t2y)}')
        plt.xlabel('Tempo em segundos.')
        plt.ylabel('Temperatura em °C')
        plt.plot(t2x, t2y)
        plt.savefig(file)
        plt.clf()
    except (ValueError, Exception) as e:
        raise e


class Worker(QObject):
    finalizar = pyqtSignal()
    barraProgresso = pyqtSignal(int)
    saidaInfoInicio = pyqtSignal(str)
    saidaDadosLCD = pyqtSignal(list)
    saidaData = pyqtSignal(str)
    saidaDadosEmail = pyqtSignal(str, float, float, float, float, float, float,
                                 float, float, float, float, float, float, str, str, str)
    mostradorTempoRestante = pyqtSignal(int)

    def __init__(self, portaArduino: Serial, tempoGrafico: int, parent=None) -> None:
        super().__init__(parent)
        self.mutex = QMutex()
        self.porta: Serial = portaArduino
        self.paradaPrograma: bool = False
        self.tempoConvertido: int = tempoGrafico
        self.arduino = portaArduino

    def porcentagem(self, totalVoltas: int, voltaAtual: int) -> int:
        porcentagem: float = voltaAtual * 100 / totalVoltas
        return int(porcentagem)

    @pyqtSlot()
    def parar(self):
        self.mutex.lock()
        self.paradaPrograma: bool = True
        self.mutex.unlock()

    @pyqtSlot()
    def run(self):
        try:
            caminhoDiretorio: str = os.path.dirname(os.path.realpath(__file__))

            if os.path.isfile('EMAIL_USER_DATA.txt'):
                self.saidaInfoInicio.emit('Arquivo "EMAIL_USER_DATA.txt" já existe.')
            else:
                define_arquivo()
                self.saidaInfoInicio.emit('Arquivo "EMAIL_USER_DATA.txt" foi criado, por favor, configure antes de continuar.')
            c3 = count()
            contador3: int = next(c3)
            bufferDadosRecebidosArduino: dict = {
                'u': '',
                'p': '',
                '1': '',
                '2': ''
            }
            while not self.paradaPrograma:
                if contador3 == 0:
                    tempo_graf = self.tempoConvertido
                    self.saidaInfoInicio.emit(f'Inicio: --> {data()} <--')
                else:
                    self.saidaInfoInicio.emit(f'Parcial {contador3} --> {data()} <--')

                inicio: str = data()

                yDadosUmidade: list = []
                yDadosPressao: list = []
                yDadosTemperaturaInterna: list = []
                yDadosTemperaturaExterna: list = []

                dadosRecebidosArduino: dict = {
                    'u': '',
                    'p': '',
                    '1': '',
                    '2': ''
                }
                c2 = count()
                contador2: int = next(c2)
                contadorDadosRestantes: int = 0
                while (contador2 < tempo_graf) and not self.paradaPrograma:
                    tempoInicial = time.time()
                    c1 = count()
                    contador1: int = next(c1)
                    while contador1 < 4:
                        try:
                            dado = str(self.arduino.readline())
                            dado = dado[2:-5]
                            if float(dado[1:].strip()) == nan:
                                ...
                            if float(dado[1:]) <= 0:
                                dadosRecebidosArduino['u'] = bufferDadosRecebidosArduino['u'] if bufferDadosRecebidosArduino['u'] != 0 else ...
                                dadosRecebidosArduino['p'] = bufferDadosRecebidosArduino['p'] if bufferDadosRecebidosArduino['p'] != 0 else ...
                                dadosRecebidosArduino['1'] = bufferDadosRecebidosArduino['1'] if bufferDadosRecebidosArduino['1'] != 0 else ...
                                dadosRecebidosArduino['2'] = bufferDadosRecebidosArduino['2'] if bufferDadosRecebidosArduino['2'] != 0 else ...
                            else:
                                if dado[0] == 'u':
                                    dadosRecebidosArduino['u'] = float(dado[1:].strip())
                                    bufferDadosRecebidosArduino['u'] = float(dado[1:].strip())
                                if dado[0] == 'p':
                                    dadosRecebidosArduino['p'] = float(dado[1:].strip())
                                    bufferDadosRecebidosArduino['p'] = float(dado[1:].strip())
                                if dado[0] == '1':
                                    dadosRecebidosArduino['1'] = float(dado[1:].strip())
                                    bufferDadosRecebidosArduino['1'] = float(dado[1:].strip())
                                if dado[0] == '2':
                                    dadosRecebidosArduino['2'] = float(dado[1:].strip())
                                    bufferDadosRecebidosArduino['2'] = float(dado[1:].strip())
                        except Exception:
                            ...
                        finally:
                            self.arduino.reset_output_buffer()
                        contador1 = next(c1)
                    dadosLcd: list = []
                    dadosLcd.append(dadosRecebidosArduino["u"])
                    dadosLcd.append(dadosRecebidosArduino["p"])
                    dadosLcd.append(dadosRecebidosArduino["1"])
                    dadosLcd.append(dadosRecebidosArduino["2"])
                    self.saidaData.emit(data())
                    self.saidaDadosLCD.emit(dadosLcd)
                    with open(dataDoArquivo(), 'a+', newline='', encoding='utf-8') as log:
                        try:
                            w = csv.writer(log)
                            w.writerow([data(), dadosRecebidosArduino['u'], dadosRecebidosArduino['p'],
                                        dadosRecebidosArduino['1'], dadosRecebidosArduino['2']])
                            yDadosUmidade.append(float(dadosRecebidosArduino['u']))
                            yDadosPressao.append(float(dadosRecebidosArduino['p']))
                            yDadosTemperaturaInterna.append(float(dadosRecebidosArduino['1']))
                            yDadosTemperaturaExterna.append(float(dadosRecebidosArduino['2']))
                        except ValueError:
                            ...
                    contador2 = next(c2)
                    percent: int = self.porcentagem(tempo_graf, contador2)
                    self.barraProgresso.emit(percent)
                    tempoRestante = tempo_graf
                    self.mostradorTempoRestante.emit((tempoRestante - contadorDadosRestantes) - 1)
                    contadorDadosRestantes += 1
                    tempoFinal: float = time.time()
                    while tempoFinal - tempoInicial < 1:
                        tempoFinal = time.time()
                contador3 = next(c3)
                plot_umidade(yDadosUmidade, inicio, caminhoDiretorio)
                plot_pressao(yDadosPressao, inicio, caminhoDiretorio)
                plot_temp1(yDadosTemperaturaInterna, inicio, caminhoDiretorio)
                plot_temp2(yDadosTemperaturaExterna, inicio, caminhoDiretorio)
                self.saidaDadosEmail.emit(
                                inicio,
                                round(mean(yDadosUmidade), 2),
                                round(mean(yDadosPressao), 2),
                                round(mean(yDadosTemperaturaInterna), 2),
                                round(mean(yDadosTemperaturaExterna), 2),
                                maximos(yDadosTemperaturaInterna),
                                minimos(yDadosTemperaturaInterna),
                                maximos(yDadosTemperaturaExterna),
                                minimos(yDadosTemperaturaExterna),
                                maximos(yDadosUmidade),
                                minimos(yDadosUmidade),
                                maximos(yDadosPressao),
                                minimos(yDadosPressao),
                                inicio,
                                data(),
                                caminhoDiretorio)
            self.saidaInfoInicio.emit('Programa Parado !!!')
            self.barraProgresso.emit(0)
            self.finalizar.emit()
        except (ValueError, Exception) as e:
            self.saidaInfoInicio.emit(f'{e.__class__.__name__}: {e}')
            self.saidaInfoInicio.emit('Programa Parado !!!')
            self.barraProgresso.emit(0)
            self.finalizar.emit()


class EntradaError(Exception):
    ...


class DadosError(Exception):
    ...


class ConexaoUSB():
    def __init__(self, caminhoPorta: str) -> None:
        self.caminho: str = caminhoPorta

    def conectPortaUSB(self) -> Serial:
        try:
            conexaoArduino: Serial = Serial(self.caminho, 9600, timeout=2, bytesize=serial.EIGHTBITS)
            conexaoArduino.reset_input_buffer()
            return conexaoArduino
        except Exception as e:
            raise e


class InterfaceEstacao(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        super().setupUi(self)
        self.btnInciarEstacao.clicked.connect(self.execucaoMainEstacao)
        self.btnPararEstacao.clicked.connect(self.pararWorker)
        self.btnPararEstacao.setEnabled(False)
        self.modeloInfo = QStandardItemModel()
        self.saidaDetalhes.setModel(self.modeloInfo)

    def mostrardorDisplayBarraProgresso(self, percent):
        self.barraProgresso.setValue(percent)

    def mostradorDisplayInfo(self, info):
        self.modeloInfo.appendRow(QStandardItem(info))

    def mostradorDisplayLCDTempoRestante(self, valor):
        self.visorTempoRestante.display(valor)
        self.visorTempoRestante_2.display(valor)

    def mostradorDisplayLCDTempoDefinido(self, valor):
        self.tempoDefinido.display(valor)
        self.tempoDefinido_2.display(valor)

    def mostradorDisplayLCDDados(self, dados: list):
        self.dadoUmidade.display(dados[0])
        self.dadoPressao.display(dados[1])
        self.dadoTempInterna.display(dados[2])
        self.dadoTempExterna.display(dados[3])

    def mostradorLabelDataHora(self, dt_hr):
        self.dadosHoraData.setText(dt_hr)

    def retornarBotoesInicio(self):
        self.btnInciarEstacao.setEnabled(True)
        self.btnPararEstacao.setEnabled(False)

    def execucaoMainEstacao(self):
        self.btnInciarEstacao.setEnabled(False)
        self.btnPararEstacao.setEnabled(True)
        self.porta = self.portaArduino.text()
        if self.porta == '':
            self.mostradorDisplayInfo('Entre com uma porta válida.')
            self.retornarBotoesInicio()
            return
        try:
            self.receptorTempoGraficos = self.tempoGraficos.text()
            t = TransSegundos(self.receptorTempoGraficos)
            self.receptorTempoGraficos = t.conversorHorasSegundo()
            self.mostradorDisplayLCDTempoDefinido(self.receptorTempoGraficos)
            if self.receptorTempoGraficos <= 0:
                self.retornarBotoesInicio()
                raise EntradaError('Tempo não pode ser menor ou igual a Zero.')
        except Exception as e:
            self.mostradorDisplayInfo(f'{e.__class__.__name__}: {e}')
            return
        try:
            portaArduino: ConexaoUSB = ConexaoUSB(self.porta)
            pA: Serial = portaArduino.conectPortaUSB()
            self.thread = QThread(parent=self)
            self.worker = Worker(portaArduino=pA, tempoGrafico=self.receptorTempoGraficos)
            self.worker.moveToThread(self.thread)
            self.worker.finalizar.connect(self.thread.quit)
            self.worker.finalizar.connect(self.worker.deleteLater)
            self.worker.finalizar.connect(self.thread.deleteLater)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
            self.worker.barraProgresso.connect(self.mostrardorDisplayBarraProgresso)
            self.worker.saidaInfoInicio.connect(self.mostradorDisplayInfo)
            self.worker.saidaDadosLCD.connect(self.mostradorDisplayLCDDados)
            self.worker.saidaData.connect(self.mostradorLabelDataHora)
            self.worker.saidaDadosEmail.connect(self.executarEmail)
            self.worker.mostradorTempoRestante.connect(self.mostradorDisplayLCDTempoRestante)
            self.thread.finished.connect(lambda: self.btnInciarEstacao.setEnabled(True))
            self.portaArduino.setEnabled(False)
            self.tempoGraficos.setEnabled(False)
        except Exception as e:
            self.mostradorDisplayInfo(f'{e.__class__.__name__}: {e}')
            self.retornarBotoesInicio()
            return

    def pararWorker(self):
        self.worker.parar()
        self.thread.quit()
        self.thread.wait()
        self.btnPararEstacao.setEnabled(False)
        self.portaArduino.setEnabled(True)
        self.tempoGraficos.setEnabled(True)

    def executarEmail(self, inicio, umi, press, t1, t2, t1max,
                      t1min, t2max, t2min, umimax, umimini,
                      pressmax, pressmini, ini, fim, path):
        try:
            self.emailThread = QThread(parent=None)
            self.emailWorker = EmailWorker(inicio=inicio, umi=umi, press=press, t1=t1,
                                           t2=t2, t1max=t1max, t1min=t1min, t2max=t2max,
                                           t2min=t2min, umimax=umimax, umimini=umimini,
                                           pressmax=pressmax, pressmini=pressmini,
                                           ini=ini, fim=fim, path=path)
            self.emailWorker.moveToThread(self.emailThread)
            self.emailThread.started.connect(self.emailWorker.run)
            self.emailThread.start()
            self.emailWorker.msgEnvio.connect(self.mostradorDisplayInfo)
            self.emailWorker.termino.connect(self.emailThread.quit)
            self.emailWorker.termino.connect(self.emailWorker.deleteLater)
            self.emailWorker.termino.connect(self.emailThread.deleteLater)
        except Exception as e:
            self.mostradorDisplayInfo(f'{e.__class__.__name__}: {e}')
            return


if __name__ == '__main__':
    qt = QApplication(sys.argv)
    iuEstacao = InterfaceEstacao()
    iuEstacao.show()
    qt.exec_()
