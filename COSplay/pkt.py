"""
This file is based on Dave Hylands json-ipc/json_pkt.py
(https://github.com/dhylands/json-ipc.git).
"""

try:
	#imports for pyboard
	from utime import sleep
	import tsv
	from dump_mem import dump_mem
except ImportError:
	#imports on host computer
	from time import sleep
	try:
		#if COSplay is installed as package
		from COSplay import tsv
		from COSplay.dump_mem import dump_mem
	except ImportError:
		#if cli.py is executed directly
		import tsv
		from dump_mem import dump_mem


SOH = 0x01			#start of header
STX = 0x02			#start of text
ETX = 0x03			#end of text
EOT = 0x04			#end of transmission
SEQ = 0x05			#type of data is a sequence (json)
MSG = 0x06			#type of data is message for user from pyboard
INS = 0x07			#instruction form pyboard to server 
# <SOH><LenLow><LenHigh><TYPE><STX><PAYLOAD><ETX><LRC><EOT>

def lrc(str):
	"""Compute longitudinal redundancy check.

	   Parameters
	   ----------
	   str : string
	       Input byte string.

	   Returns
	   -------
	   int
	       Longitudinal redundancy of input string.
	"""
	sum = 0
	try:
		for b in str:
			sum = (sum + b) & 0xff
		return ((sum ^ 0xff) + 1) & 0xff
	except TypeError:
		for b in str:
			sum = (sum + ord(b)) & 0xff
		return ((sum ^ 0xff) + 1) & 0xff

class Packet:
	"""Package data and send/receive it via serial port.

	   This class packs data and sends/receives it via the
	   serial_port. Do not change the value of the Attributes listed
	   below. Use them as follows: ``p.send(p.ANS_yes)``, where ``p``
	   is an instance of the this class.

	   Parameters
	   ----------
	   serial_port : COSplay.serial_port object
	       Serial port used for sending and receiving data.
	   show_packets : bool, optional
	       If true every received byte is printed on the screen in
	       hex and ascii representation.

	   Attributes
	   ----------
	   ANS_yes : int
	       Positive answer to instructions/questions form pyboard.
	   ANS_no : int
	       Negative answer to instructions/questions form pyboard.
	   INS_check_for_sequences_on_server : int
	       Instruction to check for COSgen folder on host computer.
	   INS_ask_user : int
	       Instruction to ask user whether to use sequences stored on
	       microcontroller or host computer.
	   INS_send_sequences : int
	       Instruction to send sequences to microcontroller.
	   
	"""

	STATE_SOH = 0
	STATE_LEN_0 = 1
	STATE_LEN_1 = 2
	STATE_TYPE = 3
	STATE_STX = 4
	STATE_PAYLOAD = 5
	STATE_ETX = 6
	STATE_LRC = 7
	STATE_EOT = 8

	ANS_no = 0				#answers form server to instructions/questions form pyboardi
	"""Negative answer to instructions/questions form pyboard."""
	ANS_yes = 1
	INS_check_for_sequences_on_server = 2	#check for COSgen folder on host computer
	INS_ask_user = 3			#ask user whether to use sequences stored on microcontroller or host computer
	INS_send_sequences = 4			#send sequences to microcontroller

	def __init__(self, serial_port, show_packets=False):
		self.serial_port = serial_port
		self.show_packets = show_packets
		self.pkt_len = 0
		self.pkt_type = None
		self.pkt_idx = 0
		self.pkt = None
		self.lrc = 0
		self.state = Packet.STATE_SOH

	def send(self, obj):
		"""Convert a python object into its string representation and then send
    	    	   it using the 'serial_port' passed in the constructor.

		   Parameters
		   ----------
		   obj : list, string or int
		       object that is send via 'serial_port'
    	    	"""
		data_type = type(obj)
		payload_str = None
		payload_len = None
		payload_lrc = None
		if data_type is list:
			payload_str = tsv.dumps(obj).encode('ascii')
			payload_len = len(payload_str)
			payload_lrc = lrc(payload_str)			#longitudinal redundancy check
			hdr = bytearray((SOH, payload_len & 0xff, payload_len >> 8, SEQ, STX)) #header & 0xff masks the lower eight bits(FF is 255) >>8 means shift to the right by 8 bits 
		elif data_type is str:
			payload_str = obj.encode('ascii')
			payload_len = len(payload_str)
			payload_lrc = lrc(payload_str)
			hdr = bytearray((SOH, payload_len & 0xff, payload_len >> 8, MSG, STX))
		elif data_type is int:
			payload_str = str(obj).encode('ascii')
			payload_len = len(payload_str)
			payload_lrc = lrc(payload_str)
			hdr = bytearray((SOH, payload_len & 0xff, payload_len >> 8, INS, STX))
		else:
			raise TypeError("Type cannot be send using Packet.")
		ftr = bytearray((ETX, payload_lrc, EOT))	#footer
		if self.show_packets:
			data = hdr + payload_str + ftr
			dump_mem(data, 'Send')
		self.serial_port.write(hdr)
		self.serial_port.write(payload_str)
		self.serial_port.write(ftr)


	def process_byte(self, byte):
		"""Process a single byte. Return an object when one is
    	    	   successfully parsed, otherwise returns None.

		   Parameters
		   ----------
		   byte : bytes / bytearray
		       inbut byte, For MicroPython and Python3 this
		       should be a bytes object. In Python2 a bytearray
		       can be used.

		   Returns
		   -------
		   2d array / string / int
		       Returns object if package is successfully parsed,
		       otherwise returns None.
    	    	"""
		if self.show_packets:
			if byte >= ord(' ') and byte <= ord('~'):
				print('Rcvd 0x%02x \'%c\'' % (byte, byte))
			else:
				print('Rcvd 0x%02x' % byte)
		if self.state == Packet.STATE_SOH:
			if byte == SOH:
				self.state = Packet.STATE_LEN_0
		elif self.state == Packet.STATE_LEN_0:
			self.pkt_len = byte
			self.state = Packet.STATE_LEN_1
		elif self.state == Packet.STATE_LEN_1:
			self.pkt_len += (byte << 8)
			self.state = Packet.STATE_TYPE
		elif self.state == Packet.STATE_TYPE:
			self.pkt_type = byte
			self.state = Packet.STATE_STX
		elif self.state == Packet.STATE_STX:
			if byte == STX:
				self.state = Packet.STATE_PAYLOAD
				self.pkt_idx = 0
				self.pkt = bytearray(self.pkt_len)
				self.lrc = 0
			else:
				self.state = Packet.STATE_SOH
		elif self.state == Packet.STATE_PAYLOAD:
			self.pkt[self.pkt_idx] = byte
			self.lrc = (self.lrc + byte) & 0xff
			self.pkt_idx += 1
			if self.pkt_idx >= self.pkt_len:
				self.state = Packet.STATE_ETX
		elif self.state == Packet.STATE_ETX:
			if byte == ETX:
				self.state = Packet.STATE_LRC
			else:
				self.state = Packet.STATE_SOH
		elif self.state == Packet.STATE_LRC:
			self.lrc = ((self.lrc ^ 0xff) + 1) & 0xff
			if self.lrc == byte:
				self.state = Packet.STATE_EOT
			else:
				self.state = Packet.STATE_SOH
		elif self.state == Packet.STATE_EOT:
			self.state = Packet.STATE_SOH
			if byte == EOT:
				if self.pkt_type == SEQ:
					try:				# micropython does not have decode attribute for bytearrays
						return tsv.loads(self.pkt.decode('ascii'))
					except AttributeError:
						return tsv.loads(str(self.pkt,'ascii'))
				elif self.pkt_type == MSG:
					try:
						return self.pkt.decode('ascii')
					except AttributeError:
						return str(self.pkt,'ascii')
				elif self.pkt_type == INS:
					try:
						return int(self.pkt.decode('ascii'))
					except AttributeError:
						return int(str(self.pkt,'ascii'))

	def receive(self,time_out=0):
		"""
		Try to receive an object.

		This function tries to receive an object
		until 'time_out'. If a byte is received, 'time_out'
		becomes obsolete and the function continues until an
		object is received. Returns None upon time out.

		Parameters
		----------
		time_out : int
		    Time in seconds until return if no bytes are received.
		    If time_out = 0, the function never times out.


		Returns
		-------
		object
		    Received object or None in case of time out.
		"""
		i = 0
		while time_out == 0 or i <= time_out*10:
			byte = self.serial_port.read_byte()
			if byte is not None:
				time_out=0	#once the functions starts to receive something it does not timeout anymore
				obj = self.process_byte(byte)
				if obj is not None:
					return obj
			i += 1
			if time_out != 0:
				sleep(0.1)
		return None

