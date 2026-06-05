import os
import numpy as np
import matplotlib.pyplot as plt
from natsort import natsorted

FilesPath = ""

def GetFilesInDir(dirPath: str) -> list:
    files = []
    for entry in os.listdir(dirPath):
        fullPath = os.path.join(dirPath, entry)
        if os.path.isfile(fullPath):
            files.append(fullPath)
    return natsorted(files)

def ReadDataFromFile(data: dict, filePath: str) -> None:
    print("reading data from file \"" + filePath + "\"...")
    try:
        with open(filePath, "r") as file:
            for line in file:
                elems = line.split("|")
                if (len(elems) == 7):
                    currTargetDuty = int(elems[0])
                    if (currTargetDuty not in data):
                        data[currTargetDuty] = {}
                    currCircuit = int(elems[1])
                    if (currCircuit not in data[currTargetDuty]):
                        data[currTargetDuty][currCircuit] = {}
                    currState = int(elems[2])
                    if (currState not in data[currTargetDuty][currCircuit]):
                        data[currTargetDuty][currCircuit][currState] = {"iters" : [], "timestamps" : [], "dutys" : [], "pauses" : []}
                    currPause = int(elems[3])
                    currIter = int(elems[4])
                    currTimestamp = int(elems[5])
                    currDuty = int(elems[6].replace("\n", ""))
                    data[currTargetDuty][currCircuit][currState]["iters"].append(currIter)
                    data[currTargetDuty][currCircuit][currState]["timestamps"].append(currTimestamp)
                    data[currTargetDuty][currCircuit][currState]["dutys"].append(currDuty)
                    data[currTargetDuty][currCircuit][currState]["pauses"].append(currPause)
    except Exception as e:
        print("ERROR: Exception when reading file \"" + filePath + "\" (" + str(e) + ")!")

def PlotDutyVsTime(data: dict, show: bool, savePath: str) -> None:
    for targetDuty in data:
        print("plotting duty cycle duration vs. time (" + str(targetDuty) + " CPU cycles)...")
        circuitNum = len(data[targetDuty])
        title = "$t_{duty}$ Duration Error vs. Time"
        fig, axes = plt.subplots(nrows = circuitNum, ncols = 2, figsize = (13, 10))
        fig.suptitle(title)
        circuitIdx = 0
        for circuit in data[targetDuty]:
            for state in data[targetDuty][circuit]:
                timestamps = np.array(data[targetDuty][circuit][state]["timestamps"]) / 1000000
                dutys = np.array(data[targetDuty][circuit][state]["dutys"]) - targetDuty
                pauses = np.array(data[targetDuty][circuit][state]["pauses"])
                if (len(dutys) == 0) or (len(timestamps) == 0):
                    continue
                dataLabel = "CO " + str(circuit + 1)
                if (state == 0):
                    dataLabel += ", HIGH $t_{duty}$"
                else:
                    dataLabel += ", LOW $t_{duty}$"
                plots = None
                if (circuitNum == 1):
                    plots = axes[state]
                else:
                    plots = axes[circuitIdx, state]
                plots.set_title(dataLabel)
                for i in range(len(timestamps)):
                    if (pauses[i] == 1):
                        plots.axvline(x = timestamps[i], color = "r", linewidth = 5.0, alpha = 0.3)
                plots.plot(timestamps, dutys, linewidth = 0.5, label = dataLabel)
                plots.axhline(y = -500, color = "red", linestyle = "dashed", linewidth = 0.5)
                plots.axhline(y = 500, color = "red", linestyle = "dashed", linewidth = 0.5)
                plots.set_xlim(min(timestamps), max(timestamps))
                plots.set_ylim(-1000, 1000)
                plots.grid(which = "both")
            circuitIdx += 1
        fig.supxlabel("Time (s)")
        fig.supylabel("$t_{duty}$ Error (CPU cycles)")
        plt.tight_layout()
        if (len(savePath) > 0):
            fileDirPath = os.path.dirname(savePath) + "\\plots\\duration_v_time\\" + str(targetDuty) + "\\"
            fileName = os.path.basename(savePath).replace(".txt", "")
            fullSavePath = fileDirPath + fileName + ".png"
            os.makedirs(fileDirPath, exist_ok = True)
            plt.savefig(fullSavePath)
        if (show):
            plt.show()
        plt.clf()
        plt.close()

def main():
    print("---- SCRIPT STARTED ----\n")

    files = GetFilesInDir(FilesPath)
    for filePath in files:
        if (filePath.endswith(".txt") or filePath.endswith(".TXT")):
            currData = {}
            ReadDataFromFile(currData, filePath)
            PlotDutyVsTime(currData, True, filePath)

    print("\n\n---- SCRIPT FINISHED ----")

if (__name__ == "__main__"):
    main()