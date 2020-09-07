import math
import random
import itertools
from decimal import *
from PIL import Image, ImageDraw, ImageTk

# generate the output map
# mapIn - your initial dataset 
# - format is [(Name, [x,y...]),(Name, [x,y...])...]
# iterations - for how many iterations you'd like the generation loop to run
# dimOut - the desired dimension of the output map
# errorMap - returns a tuple that consisting of the resulting map itself, as well as an array of the errors for each pair distance. useful for image generation with error indication.
# verbose - controls console logging. for verbose = n, the console will log every nth iteration
def generateMap(mapIn, iterations, dimOut, errorMap=False, verbose = 0):
	dimIn = len(mapIn[0][1])
	mapSize = len(mapIn)

	def getPrecision(n):
		if n == 0:
			return 1
		if n % 10 == 0:
			i = 1
			while(n%10==0):
				i=+1
				n/=10
			return i
		n = str(n)
		n=n.replace('.','')
		return len(n)

	#figure out what sigfig to round to. helps us figure out when the map converges 
	precision = 0
	for item in mapIn:
		for c in item[1]:
			precision+=getPrecision(c)
	precision/=mapSize*dimIn
	precision = round(precision)
	getcontext().prec = precision

	# find center of mass for mapIn. needed to calculate the radius, which is in turn needed to initialize the output map
	center = [0]*dimIn
	for item in mapIn:
		for coord in range(dimIn):
			center[coord]+=item[1][coord]
	center = [(i/mapSize) for i in center]

	# helper function
	# simple euclidean distance function. assumes each point is of the same dimension (as it should be)
	def distance(a, b):
		dim=len(a)
		distances = [abs(a[i]-b[i]) for i in range(dim)]
		s=0
		for c in distances:
			s+=c**2
		return math.sqrt(s)


	# find the average radius (average distance from the center of mass)
	avgRadius = sum([distance(center,i[1]) for i in mapIn])/mapSize

	# the initial increment size is the average radius
	increment = avgRadius

	# initialize mapOut
	# each item from the map starts at a random point in space within the bounds an n-cube of length avgRadius (found above)
	
	mapOut=[]

	for i in range(mapSize):
		coordinates = []
		for n in range(dimOut):
			coordinates.append(random.uniform(-1,1)*avgRadius)
		mapOut.append([mapIn[i][0],coordinates])
	
	#helper functions

	def doOption(index, option):
		coordinates = []+mapOut[index][1]
		if option != 0:
			coordinates[abs(option)-1]+=option/abs(option)*increment
		return coordinates

	# returns the error between two distances
	# c&d are true points
	def pairError(a,b,c,d):
		realDistance = distance(c,d)
		distanceOut = distance(a,b)
		absError = abs(realDistance-distanceOut)
		return absError/realDistance

	# returns the average error of all distances including the given item, after the given option if performed on it
	def avgOptionError(index, option):
		avg = 0
		realCoordinates = mapIn[index][1]
		coordinates = doOption(index, option)
		for i in range(mapSize):
			if i == index:
				continue
			avg+=pairError(coordinates,mapOut[i][1],realCoordinates,mapIn[i][1])
		avg/=(mapSize-1)
		return avg

	# returns an array containing the errors for every pair distance in the map
	def errorMap():
		pairs = itertools.combinations(range(mapSize),2)
		return [pairError(mapOut[i[0]][1],mapOut[i[1]][1],mapIn[i[0]][1],mapIn[i[1]][1]) for i in pairs]

	# returns the discrepancy from the input map of all pair distances in mapOut
	def avgMapError():
		return sum(errorMap())/(math.factorial(mapSize)/(2*math.factorial(mapSize-2)))


	def doNothing(i):
		pass

	def consoleLog(w):
		if w % verbose == 0:
			print(f"Iteration {w}. Average error of {avgMapError()}. Increments of {increment}.")
			
	doConsole = doNothing
	if verbose > 0:
		doConsole = consoleLog

	error=None
	w=0
	while w < iterations:
		doConsole(w)
		for index in range(mapSize):
			bestError = float("inf")	
			bestOption = None	
			for i in range(-1*(dimOut),dimOut+1):
				a = avgOptionError(index, i)
				if a < bestError:
					bestError = a
					bestOption = i
			mapOut[index][1] = doOption(index,bestOption)
		lastError = error
		error = avgMapError()
		if lastError == error:
			# if the next increment still has a significant effect on the position of the items given our significant figures, step down the increment
			if Decimal(0.0)+Decimal(avgRadius+increment/10) != Decimal(0.0)+Decimal(avgRadius):
				increment/=10
			elif verbose>0:
				print(f"Converged on an error of {error} after {w} iterations.")
				break
		w+=1

	# it didn't technically converge if it just ran out of iterations.
	if(w==iterations and verbose>0):
		print(f"Reached an error of {error} after {w} iterations.")
	if errorMap:
		return (mapOut,errorMap())
	else:
		return mapOut

# i probably could've just used matplotlib, but i kinda like the way this one looks
# returns a PIL image. You'll have to use .show() or write it to a file to view it.
# mapsIn - the map to generate an image of. must include an error map, because of error indication
# width - the width of your image in pixels. height is calculated based on this
# radius - pixel radius of the points on the image
# background color
# point color
# text color (label)
# dims - specify the dimensions of your plane if you want to include some empty space. useful for live image gen
# unit - the unit to use on the legend
# indicators - the error indication desired, in a list of tuples. currently accepts these as list items:
# 	('line', threshold, color, doText) draws a line tracing distances that have an error over a given threshold
# 		threshold - the minimum threshold for which a line will be drawn
# 		color - the color of the line
#		doText - draw text specifying how erroneous the distance is
# 	('halo', color) - draws a halo around the item with a radius proportional to the error
# 	('text', color) - simply draws text specifying the average error for each item
def generateImage(mapsIn, width, radius=5, backgroundColor = 'black', pointColor = 'white', textColor = 'white', dims=(), unit = "Unit", indicators = ()):

	mapIn = mapsIn[0]

	# set image bounds
	minX = float("inf")
	maxX = -1*(float("inf"))
	minY = float("inf")
	maxY = -1*(float("inf"))
	for item in mapIn:
		x = item[1][0]
		y = item[1][1]
		minX = min(minX, x)
		maxX = max(maxX, x)
		minY = min(minY, y)
		maxY = max(maxY, y)

	margin = round(0.15*width)
	margin = min(150, margin)
	margin = max(60, margin)
	centerX = (minX+maxX)/2
	centerY = (minY+maxY)/2
	if dims == ():
		matrixWidth = maxX-minX
		matrixHeight = maxY-minY
	else:
		matrixWidth = dims[0]
		matrixHeight = dims[1]
	scaleFactor = matrixWidth/(width-margin*2)

	# infer pixel height
	height = round(matrixHeight/scaleFactor)+margin*2

	# initialize PIL image
	img = Image.new('RGB', (width, height), color=backgroundColor)
	d=ImageDraw.Draw(img)

	#pixel midpoints
	xMid = round(width/2,1)
	yMid = round(height/2,1)

	# helper function that draws a circle of radius r around point (x,y)
	def drawCircle(x,y,r,color):
		d.ellipse([x-r,y-r,x+r,y+r], fill=color)

	# helper function that returns the pixel coordinates of the map item with the given index
	def toPixels(index):
		x = mapIn[index][1][0]
		y= mapIn[index][1][1]
		convertedX = xMid + round((x-centerX)/scaleFactor)
		convertedY = yMid + round((y-centerY)/scaleFactor)
		return [convertedX,convertedY]

	# conditionally define the procedure that happens for each item on the map
	errorList = mapsIn[1]
	mapSize = len(mapIn)
	pairs =	[i for i in itertools.combinations(range(mapSize),2)]
	itemErrorList = [0]*mapSize

	for i in range(len(pairs)):
		for ii in pairs[i]:
			itemErrorList[ii]+=errorList[i]
	itemErrorList = [i/(mapSize-1) for i in itemErrorList]

	def lineFunction(threshold, color, doText):
		if threshold == -1:
			print("No threshold specified for line indication. Skipping...")
			return
		def drawText(x1,y1,x2,y2,e):
			spacer = 20
			xMid = (x1+x2)/2
			yMid = (y1+y2)/2
			angle = (math.pi)/2 if ((y1-y2)==0) else math.atan((x1-x2)/(y1-y2))
			textX = round(xMid+(spacer*math.cos(angle)))
			textY = round(yMid-(spacer*math.sin(angle)))
			d.text([textX,textY],str(e),fill=color)
		if doText:
			textFunction = drawText
		else:
			textFunction = lambda a,b,c,d,e:None

		for i in range(len(pairs)):
			error = errorList[i]
			if error>=threshold:
				a = toPixels(pairs[i][0])
				b = toPixels(pairs[i][1])
				x1 = a[0]
				x2 = b[0]
				y1 = a[1]
				y2 = b[1]

				d.line([(x1,y1),(x2,y2)],fill=color)
				textFunction(x1,y1,x2,y2,round(error,3))

	def haloFunction(color):
		radiusScale = abs(max(itemErrorList))/radius
		for i in range(mapSize):
			coords = toPixels(i)
			haloRadius = round(radius+(itemErrorList[i]/radiusScale))
			drawCircle(coords[0],coords[1],haloRadius,color)

	def pointFunction():
		for i in range(mapSize):
			coords = toPixels(i)
			x = coords[0]
			y = coords[1]

			drawCircle(x,y,radius,pointColor)
			
			textx = x
			texty= y+5+radius

			d.text([textx,texty], mapIn[i][0], fill=textColor)

	def textFunction(color):
		for i in range(mapSize):
			error = itemErrorList[i]
			coords = toPixels(i)
			d.text((coords[0],coords[1]-radius*4),str(round(error,3)),fill=color)



	procedures = ['line','halo','point','text']
	dictionary = {
		'line' : lineFunction,
		'halo' : haloFunction,
		'point' : pointFunction,
		'text' : textFunction
	}
	
	indicators=list(indicators)
	indicators.append(('point',))
	indicators.sort(key=lambda a : procedures.index(a[0]))

	for i in indicators:
		dictionary[i[0]](*i[1:])

	# draws the legend
	unitLength = round(1/scaleFactor)
	leftEnd = (round(margin*0.15),height-round(margin*0.25))
	rightEnd = (round(margin*0.15)+unitLength,height-round(margin*0.25))
	d.line((leftEnd, rightEnd), fill ='white')
	d.line((leftEnd, (leftEnd[0],leftEnd[1]-round(0.0333*margin))),fill = 'white')
	d.line((rightEnd, (rightEnd[0],rightEnd[1]-round(0.0333*margin))),fill = 'white')
	d.text((leftEnd[0],leftEnd[1]+round(0.0467*margin)),"One "+unit, fill='white')
	
	return img
hundredStars=[['Sol', [0, 0, 0]], ['Alpha and Proxima Centauri', [-1.643, -1.374, -3.838]], ["Barnard's Star", [-0.0566, -5.92, 0.486]], ['Wolf 359', [-7.416, 2.193, 0.993]], ['Lalande 21185', [-6.523, 1.646, 4.882]], ['UV Ceti', [7.417, 3.318, -2.673]], ['Sirius', [-1.612, 8.078, -2.474]], ['Ross 154', [1.912, -8.658, -3.917]], ['Ross 248', [7.414, -0.667, 7.169]], ['Epsilon Eridani', [6.197, 8.294, -1.725]], ['Lacaille 9352', [8.457, -2.036, -6.286]], ['Ross 128', [-10.87, 0.582, 0.153]], ['EZ Aquarii', [9.96, -3.84, -2.98]], ['Procyon', [-4.769, 10.31, 1.039]], ['61 Cygni', [6.489, -6.109, 7.152]], ['Struve 2398', [1.092, -5.781, 10.04]], ['Groombridge 34', [8.341, 0.671, 8.087]], ['Southern Infrared Proper motion Survey 1259-4336', [-8.3, -2.2, -8.1]], ['DX Cancri', [-6.3, 8.45, 5.36]], ['Epsilon Indi', [5.658, -3.157, -9.896]], ['Tau Ceti', [10.28, 5.018, -3.267]], ['Gliese & Jahreiss 1061', [5.0, 6.89, -8.37]], ['YZ Ceti', [11.1, 3.5, -3.62]], ["Luyten's Star", [-4.592, 11.45, 1.128]], ["Teegarden's Star", [8.64224, 8.1304, 3.60114]], ["Kapteyn's Star", [1.89, 8.832, -9.038]], ['AX Microscopii', [7.6, -6.534, -8.078]], ['DO Cephei', [6.43, -2.73, 11.0]], ['Deep Near-Infrared Survey 1048-39', [-9.6, 3.108, -8.448]], ['V577 Monoceri', [-1.721, 13.35, -0.661]], ['Wolf 1061', [-5.177, -12.54, -3.049]], ['FL Virginis', [-13.7, -1.86, 2.27]], ["van Maanen's Star", [13.78, 2.836, 1.269]], ['Cordoba Durchmusterung -37°15492', [11.3, 0.267, -8.63]], ['Luyten 1159-16', [12.4, 6.97, 3.24]], ['Luyten 143-23', [-6.71, 2.35, -12.8]], ['Luyten Palomar 731-58', [-13.7, 4.62, -2.83]], ['AOe 17415-6', [-0.56, -5.422, 13.73]], ['Cordoba Durchmusterung -46°11540', [-1.378, -10.02, -10.8]], ['CC 658', [-6.395, 0.399, -13.64]], ['Giclas 158-27', [15.2, 0.28, -2.08]], ['Ross 780', [14.24, -4.266, -3.778]], ['V1581 Cygni', [5.18, -9.72, 10.7]], ['WX Ursae Majoris', [-11.11, 2.693, 10.85]], ['Groombridge 1618', [-9.193, 4.716, 12.08]], ['AD Leonis', [-13.5, 6.53, 5.5]], ['Cordoba Durchmusterung -49°13515', [8.48, -6.3, -12.16]], ['Cordoba Durchmusterung -44°11909', [-1.18, -11.7, -11.5]], ['Omicron(2) Eridani', [7.195, 14.63, -2.191]], ['EV Lacertae', [11.2, -3.7, 11.5]], ['70 Ophiuchi', [0.394, -16.57, 0.723]], ['Altair', [7.703, -14.68, 2.586]], ['Heintz 299', [16.3, 1.1, -4.72]], ['Giclas 9-38', [-11.1, 11.6, 5.82]], ['Giclas 99-49', [0.2, 17.5, 0.83]], ['Catalogue Astrographique +79°3888', [-3.443, 0.185, 17.24]], ['Bonner Durchmusterung +15°2620', [-15.33, -7.62, 4.552]], ['Luyten Half-Second 1723', [4.44, 17.2, -2.16]], ['Stein 2051', [3.5, 8.58, 15.4]], ['Wolf 294', [-3.35, 14.6, 9.89]], ['Luyten 347-14', [4.29, -12.3, -13.3]], ['Bonner Durchmusterung -3°1123', [2.301, 18.38, -1.191]], ['Wolf 630', [-5.15, -17.8, -2.71]], ['Sigma Draconis', [2.564, -6.014, 17.64]], ['Gliese 229', [-0.806, 17.46, -7.014]], ['Ross 47', [1.67, 18.4, 4.08]], ['Luyten 205-128', [-0.6, -10.2, -16.0]], ['Bonner Durchmusterung +4°4048', [6.284, -18.01, 1.726]], ['Luyten 674-15', [-9.63, 15.0, -7.0]], ['Gliese 570', [-12.82, -12.54, -7.034]], ['YZ Canis Minoris', [-8.52, 17.3, 1.2]], ['Cordoba Durchmusterung -40°9712', [-8.743, -11.63, -12.77]], ['Eta Cassiopeiae', [10.11, 2.198, 16.43]], ['36 Ophiuchi', [-3.37, -17.08, -8.716]], ['Bonner Durchmusterung +1°4774', [19.43, -0.916, 0.816]], ['J. Herschel 5173', [8.639, -13.41, -11.63]], ['82 Eridani', [9.285, 11.06, -13.5]], ['Delta Pavonis', [4.285, -6.809, -18.22]], ['Bonner Durchmusterung -11°3759', [-15.2, -12.1, -4.32]], ['Eggen/Greenstein white dwarf 372', [-0.32, -6.56, 18.9]], ['SFT 1321', [-9.13, 8.05, 16.0]], ['Cordoba Durchmusterung -45°13677', [7.87, -11.9, -14.35]], ['Luyten Palomar 914-54', [-13.0, -12.3, -9.5]], ['EQ Pegasi', [19.0, -2.35, 6.95]], ['Gliese 581', [-13.1, -15.5, -2.75]], ['Kuiper 79', [-2.99, -14.1, 14.7]], ['QY Aurigae', [-4.88, 15.5, 12.9]], ['Eggen/Greenstein white dwarf 45', [0.67, 21.0, -1.52]], ['Wolf 629', [-5.83, -20.1, -3.07]], ['Bonner Durchmusterung +56°2966', [11.3, -2.336, 17.88]], ['Gliese & Jahreiss 1156', [-20.9, -1.51, 4.22]], ['Gliese 625', [-5.024, -11.47, 17.43]], ['Catalogue Astrographique +23°468-46', [-19.2, 5.15, 8.38]], ['Xi Boötis', [-15.14, -14.04, 7.151]], ['Catalogue Astrographique +17°534-105', [16.6, -12.8, 6.67]], ['Ross 619', [-11.6, 18.4, 3.45]], ['Luyten Palomar 771-095', [15.0, 15.3, -6.39]], ['Bonner Durchmusterung +15°4733', [20.7, -5.88, 6.397]], ['Wolf 358', [-21.3, 6.63, 2.67]], ['Luyten 97-12', [-4.05, 7.56, -20.8]], ['Melbourne Observatory 4', [-3.3, -18.0, -13.0]]]

g = generateMap(hundredStars[:30], 500, 2, verbose = 10, errorMap=True)
generateImage(g, 800, indicators = [('line',.80, 'blue',True),('text','red')]).show()