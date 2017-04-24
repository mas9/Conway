from mpi4py import MPI
from random import randint

m = 100
n = 100
row = m + 2
col = n + 2
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

def generate_board():
	board = [[4 for j in range(col)] for i in range(row)]

	# build random 100x100 board with 1 cell thick border
	for i in range(row):
		for j in range(col):
			board[i][j] = randint(0,1)

	# replace border with 2s
	for i in range(row):
		board[i][0] = 2
		board[i][col - 1] = 2
	for j in range(col):
		board[0][j] = 2
		board[row - 1][j] = 2
	
	return board
	
def split(master):
	proc = size - 1				# the number of processes that will receive board sections/quadrants
	quad_width = (col - 2) // proc			# the width of the writable area in the majority of the sections
	quad_width_plus = (col - 2) - (quad_width * (proc - 1))			# the width for the remainder section
		
	# for the rest of the rank 0 code:
	# i is the receiving process's rank - 1
	# j is the master board's row
	# k is the master's column
		
	quad_start = 1			# the index of the first writable cell in a section
	quads = [[[4 for k in range(quad_width + 2)] for j in range(row)] for i in range(proc - 1)]		# array of sections
	for i in range(proc - 1):
		for j in range(row):
			for k in range(quad_start - 1, quad_start + quad_width + 1):
				offset = k - (i * quad_width)			# difference between section index and corresponding master index
				if (k == quad_start - 1) or (k == quad_start + quad_width):		# section right and left edges
					if master[j][k] == 0:
						quads[i][j][offset] = 2			# 2 = non-rewritable 0
					elif master[j][k] == 1:
						quads[i][j][offset] = 3			# 3 = non-rewritable 1
					else:
						quads[i][j][offset] = master[j][k]
				else:
					quads[i][j][offset] = master[j][k]
		quad_start += quad_width
			
	# this code handles the remainder section separately
	quads.append("")
	quads[proc - 1] = [[4 for k in range(quad_width_plus + 2)] for j in range(row)]
	i = proc - 1
	for j in range(row):
		for k in range(quad_start - 1, quad_start + quad_width_plus + 1):
			offset = k - (i * quad_width)
			if (k == quad_start - 1) or (k == quad_start + quad_width_plus):
			    if master[j][k] == 0:
			    	quads[i][j][offset] = 2
			    elif master[j][k] == 1:
			    	quads[i][j][offset] = 3
			    else:
			    	quads[i][j][offset] = master[j][k]
			else:
			    quads[i][j][offset] = master[j][k]

	for i in range(proc):
		comm.send(quads[i], dest = i + 1)
		
	return
	
def merge(strings):
	proc = size - 1
	updates_str = ""			# accumulator string for new board in order
		
	for i in range(m):
		for j in range(proc):
			width = n // proc
			if j == proc - 1:
				width = n - (width * (proc - 1))
			updates_str += strings[j][(i * width):((i + 1) * width)]			# slice up the process strings and shuffle them
		
	# set up template board for next timestep
	board = [[4 for j in range(col)] for i in range(row)]
	for i in range(row):
		board[i][0] = 2
		board[i][col - 1] = 2
	for j in range(col):
		board[0][j] = 2
		board[row - 1][j] = 2
			
	i = 0
	for j in range(1, m + 1):
		for k in range(1, n + 1):
			board[j][k] = int(updates_str[i])		# fill the updated array in
			i += 1
			
	return board

def print_board(board):
	for i in range(1, m + 1):
		for j in range(1, n + 1):
			print(board[i][j], end = " ")
		print()
		
	return

def main():
	if rank == 0:
		master = generate_board()				# the board before conway's rules are applied
		print_board(master)
		split(master)					# split the master board and send to processes	
		
		proc = size - 1
		updates = ["" for i in range(proc)]
		for i in range(proc):
			updates[i] = comm.recv(source = i + 1)			# get the updated subarrays
			
		step = merge(updates)			# get the next timestep
		print(20 * "-")
		print_board(step)	

	else:
		section = comm.recv(source = 0)			# this process's region to update
	
		width = len(section[0])
		update = ""					# binary string accumulator to be returned as the changes to the section
		for i in range(1, m + 1):				# iterating through writable cells
			for j in range(1, width - 1):
				live = 0				# total live cells surrounding the target
				for k in range(i - 1, i + 2):			# adjacent cells
					for l in range(j - 1, j + 2):
						if (k != i) or (l != j):			# not including the target itself
							if (section[k][l] == 1) or (section[k][l] == 3):
								live += 1
				# the actual conway rules finally!
				if (live < 2) or (live > 3):
					update += "0"
				elif live == 2:
					update += str(section[i][j])
				else:
					update += "1"
		
		comm.send(update, dest = 0)

if __name__ == '__main__':
	main()


