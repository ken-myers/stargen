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
# unit - the unit to use on the legend
# indicators - the error indication desired, in a list of tuples. currently accepts these as list items:
# 	('line', threshold, color, doText) draws a line tracing distances that have an error over a given threshold
# 		threshold - the minimum threshold for which a line will be drawn
# 		color - the color of the line
#		doText - draw text specifying how erroneous the distance is
# 	('halo', color) - draws a halo around the item with a radius proportional to the error
# 	('text', color) - simply draws text specifying the average error for each item
def generateImage(mapsIn, width, radius=5, backgroundColor = 'black', pointColor = 'white', textColor = 'white', unit = "Unit", indicators = ()):

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
	matrixWidth = maxX-minX
	matrixHeight = maxY-minY
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
