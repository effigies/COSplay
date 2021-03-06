import uos

def exists(path):
	"""
	Check if `path` exists.

	This function is the equivalent of `os.path.exists` for the pyboard.

	Parameters
	----------
	path : string

	Returns
	-------
	out : bool
	"""
	try:
		mode = uos.stat(path)
		return True
	except OSError:
		return False

def listdir_nohidden(path):
	for f in uos.listdir(path):
		if not f.startswith('.'):
			yield f
