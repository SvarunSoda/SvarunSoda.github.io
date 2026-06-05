import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from natsort import natsorted

FilesPath = ""
OperationTypes = {
    0 : "Storage",
    1 : "Copy",
    2 : "Inversion",
    3 : "Addition",
    4 : "Subtraction",
}
TDVPlotColors = {
    0 : ("blue", "blue"),
    1 : ("red", "red"),
    2 : ("green", "green")
}

def GetFilesInDir(dirPath) -> list[str]:
    files = []
    for entry in os.listdir(dirPath):
        full_path = os.path.join(dirPath, entry)
        if os.path.isfile(full_path):
            files.append(full_path)
    return natsorted(files)

def ReadDataFromFile(data: dict, filePath: str) -> None:
    print("reading data from file \"" + filePath + "\"...")
    with open(filePath, "r") as file:
        for line in file:
            elems = line.split("|")
            if (len(elems) == 11):
                currTargetDuty = int(elems[0])
                if (currTargetDuty not in data):
                    data[currTargetDuty] = {}

                currTrackType = int(elems[1])
                if (currTrackType not in data[currTargetDuty]):
                    data[currTargetDuty][currTrackType] = {}

                currTocd = int(elems[2])
                if (currTocd not in data[currTargetDuty][currTrackType]):
                    data[currTargetDuty][currTrackType][currTocd] = {}

                currTrackIdx = int(elems[3])
                if (currTrackIdx not in data[currTargetDuty][currTrackType][currTocd]):
                    data[currTargetDuty][currTrackType][currTocd][currTrackIdx] = {}

                currRunIdx = int(elems[4])
                if (currRunIdx not in data[currTargetDuty][currTrackType][currTocd][currTrackIdx]):
                    data[currTargetDuty][currTrackType][currTocd][currTrackIdx][currRunIdx] = {}

                currTdv = int(elems[5])
                currResultStatus = int(elems[6])
                currTargetPhase = int(elems[7])
                if (currTdv not in data[currTargetDuty][currTrackType][currTocd][currTrackIdx][currRunIdx]):
                    data[currTargetDuty][currTrackType][currTocd][currTrackIdx][currRunIdx][currTdv] = {"resultStatus" : currResultStatus, "iters" : [], "timestamps" : [], "targetPhase" : currTargetPhase, "phases" : []}

                currIter = int(elems[8])
                currTimestamp = int(elems[9])
                currPhase = int(elems[10].replace("\n", ""))
                data[currTargetDuty][currTrackType][currTocd][currTrackIdx][currRunIdx][currTdv]["iters"].append(currIter)
                data[currTargetDuty][currTrackType][currTocd][currTrackIdx][currRunIdx][currTdv]["timestamps"].append(currTimestamp)
                data[currTargetDuty][currTrackType][currTocd][currTrackIdx][currRunIdx][currTdv]["phases"].append(currPhase)

def GetTDVOperationName(operation: int, type: int) -> str:
    if (operation == 0):
        return "ΔΦ"
    elif (operation == 1) or (operation == 2):
        if (type == 0):
            return "ΔΦ$_{O}$"
        elif (type == 1):
            return "ΔΦ$_{R}$"
    if (type == 0):
        return "ΔΦ$_{O1}$"
    elif (type == 1):
        return "ΔΦ$_{O2}$"
    elif (type == 2):
        return "ΔΦ$_{R}$"
    return "INVALID"

def GetPhaseDiffCorrectNum(phaseDiffData: list[int], operatingCycles: int, tolerance: float) -> int:
    correctNum = 0
    for phaseDiff in phaseDiffData:
        if (abs(phaseDiff) <= round(operatingCycles * tolerance)):
            correctNum += 1
    return correctNum

def PlotValuesVsTimePerTestRunResult(data: dict, timeLimit: float, show: bool, savePath: str) -> None: #@\label{line:phaseEvaluation_PlotValuesVsTimePerTestRunResult_Start}@
    for targetDuty in data:
        for testType in data[targetDuty]:
            operation = OperationTypes[testType]
            for tocd in data[targetDuty][testType]:
                for testIdx in data[targetDuty][testType][tocd]:
                    for runIdx in data[targetDuty][testType][tocd][testIdx]:
                        print("plotting TDV values vs. time for " + operation + " (" + str(targetDuty) + ", " + str(tocd) + ", " + str(testIdx) + ", " + str(runIdx) + ")...")
                        fig, axes = plt.subplots(nrows = 1, ncols = 1, figsize = (8, 6), dpi = 300)
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            resultStatus = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["resultStatus"]
                            if (resultStatus != 2):
                                continue
                            timeData = np.array(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["timestamps"]) / 1000000
                            phaseData = (np.array(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["phases"]) / targetDuty) * 180
                            targetPhase = (data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"] / targetDuty) * 180
                            axPlot = axes
                            axPlot.plot(timeData, phaseData, c = TDVPlotColors[tdv][0], linewidth = 2, label = "Result TDV")
                            axPlot.axhline(y = targetPhase, color = TDVPlotColors[tdv][1], linewidth = 2, alpha = 0.5, linestyle = "dashed")
                            axPlot.set_xlim(0, timeLimit)
                            axPlot.set_ylim(0, 180)
                            axPlot.xaxis.set_major_locator(MultipleLocator(timeLimit / 10))
                            axPlot.yaxis.set_major_locator(MultipleLocator(45))
                            axPlot.grid(which = "both")
                            finalPhaseIdx = 0
                            for i in range(len(timeData)):
                                if (timeData[i] >= timeLimit):
                                    finalPhaseIdx = i
                                    break
                            finalPhase = phaseData[finalPhaseIdx]
                            if (finalPhase <= 180) and (finalPhase >= 0):
                                finalPhaseStr = str(round(finalPhase)) + "°"
                                for i in range(max(0, 4 - len(finalPhaseStr))):
                                    finalPhaseStr += "  "
                                axPlot.annotate(finalPhaseStr, 
                                                xy = (timeLimit, finalPhase),
                                                xytext = (timeLimit + (timeLimit * 0.02), finalPhase),
                                                xycoords = "data",
                                                textcoords = "data",
                                                ha = "left", 
                                                va = "center",
                                                arrowprops = dict(color = TDVPlotColors[tdv][0], arrowstyle = "->"),
                                                annotation_clip = False,
                                                color = TDVPlotColors[tdv][0])
                            axPlot.set_title(GetTDVOperationName(testType, tdv) + " target = " + str(round(targetPhase)) + "°", fontsize = "small")
                        if (testType == 0):
                            fig.suptitle("TDV ΔΦ vs. Time (" + operation + ", Test: " + str(testIdx) + ")")
                        else:
                            fig.suptitle("TDV ΔΦ vs. Time (" + operation + ", $t_{ocd}$: " + str(tocd) + " μs, Test: " + str(testIdx) + ", Run: " + str(runIdx) + ")")
                        fig.supxlabel("Time (s)")
                        fig.supylabel("ΔΦ (°)")
                        handles, labels = axes.get_legend_handles_labels()
                        fig.legend(handles, labels, ncols = 1, loc = "lower left", fontsize = "small")
                        plt.tight_layout()
                        if (show is True):
                            plt.show()
                        if (len(savePath) > 0):
                            fullSavePath = savePath + "operating_cycles_" + str(targetDuty) + "\\" + operation + "\\tocd_" + str(tocd) + "\\"
                            os.makedirs(fullSavePath, exist_ok = True)
                            plt.savefig(fullSavePath + "val_vs_time_test_" + str(testIdx) + "_run_" + str(runIdx) + ".png")
                        plt.clf()
                        plt.close()

def PlotValuesVsTimePerTestRunAll(data: dict, timeLimit: float, show: bool, savePath: str) -> None:
    for targetDuty in data:
        for testType in data[targetDuty]:
            operation = OperationTypes[testType]
            for tocd in data[targetDuty][testType]:
                for testIdx in data[targetDuty][testType][tocd]:
                    for runIdx in data[targetDuty][testType][tocd][testIdx]:
                        print("plotting TDV values vs. time for " + operation + " (" + str(targetDuty) + ", " + str(tocd) + ", " + str(testIdx) + ", " + str(runIdx) + ")...")
                        plotNum = 3
                        if (testType == 1) or (testType == 2):
                            plotNum = 2
                        fig, axes = plt.subplots(nrows = plotNum, ncols = 1, figsize = (8, 6), dpi = 300)
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            if (tdv >= plotNum):
                                continue
                            timeData = np.array(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["timestamps"]) / 1000000
                            phaseData = (np.array(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["phases"]) / targetDuty) * 180
                            targetPhase = (data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"] / targetDuty) * 180
                            axPlot = axes[tdv]
                            axPlot.plot(timeData, phaseData, c = TDVPlotColors[tdv][0], linewidth = 2, label = "TDV #" + str(tdv + 1))
                            axPlot.axhline(y = targetPhase, color = TDVPlotColors[tdv][1], linewidth = 2, alpha = 0.5, linestyle = "dashed")
                            axPlot.set_xlim(0, timeLimit)
                            axPlot.set_ylim(0, 180)
                            axPlot.xaxis.set_major_locator(MultipleLocator(timeLimit / 10))
                            axPlot.yaxis.set_major_locator(MultipleLocator(45))
                            axPlot.grid(which = "both")
                            finalPhaseIdx = 0
                            for i in range(len(timeData)):
                                if (timeData[i] >= timeLimit):
                                    finalPhaseIdx = i
                                    break
                            finalPhase = phaseData[finalPhaseIdx]
                            if (finalPhase <= 180) and (finalPhase >= 0):
                                finalPhaseStr = str(round(finalPhase)) + "°"
                                for i in range(max(0, 4 - len(finalPhaseStr))):
                                    finalPhaseStr += "  "
                                axPlot.annotate(finalPhaseStr, 
                                                xy = (timeLimit, finalPhase),
                                                xytext = (timeLimit + (timeLimit * 0.02), finalPhase),
                                                xycoords = "data",
                                                textcoords = "data",
                                                ha = "left", 
                                                va = "center",
                                                arrowprops = dict(color = TDVPlotColors[tdv][0], arrowstyle = "->"),
                                                annotation_clip = False,
                                                color = TDVPlotColors[tdv][0])
                            axPlot.set_title(GetTDVOperationName(testType, tdv) + " target = " + str(round(targetPhase)) + "°", fontsize = "small")
                        if (testType == 0):
                            fig.suptitle("TDV ΔΦ vs. Time (" + operation + ", Test: " + str(testIdx) + ")")
                        else:
                            fig.suptitle("TDV ΔΦ vs. Time (" + operation + ", $t_{ocd}$: " + str(tocd) + " μs, Test: " + str(testIdx) + ", Run: " + str(runIdx) + ")")
                        fig.supxlabel("Time (s)")
                        fig.supylabel("ΔΦ (°)")
                        handles, labels = [], []
                        for ax in axes.flatten():
                            h, l = ax.get_legend_handles_labels()
                            handles += h
                            labels += l
                        fig.legend(handles, labels, ncols = 3, loc = "lower left", fontsize = "small")
                        plt.tight_layout()
                        if (show is True):
                            plt.show()
                        if (len(savePath) > 0):
                            fullSavePath = savePath + "operating_cycles_" + str(targetDuty) + "\\" + operation + "\\tocd_" + str(tocd) + "\\"
                            os.makedirs(fullSavePath, exist_ok = True)
                            plt.savefig(fullSavePath + "val_vs_time_test_" + str(testIdx) + "_run_" + str(runIdx) + ".png")
                        plt.clf()
                        plt.close()  #@\label{line:phaseEvaluation_PlotValuesVsTimePerTestRunAll_End}@

def PlotErrorVsTimePerOperationResult(data: dict, tolerance: float, timeLimit: float, show: bool, savePath: str) -> None: #@\label{line:phaseEvaluation_PlotErrorVsTimePerOperationResult_Start}@
    for targetDuty in data:
        for testType in data[targetDuty]:
            operation = OperationTypes[testType]
            for tocd in data[targetDuty][testType]:
                print("plotting TDV error vs. time for " + operation + " (" + str(targetDuty) + ", " + str(tocd) + ")...")
                plotData = {0 : {}, 1 : {}, 2 : {}}
                for testIdx in data[targetDuty][testType][tocd]:
                    for runIdx in data[targetDuty][testType][tocd][testIdx]:
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            resultStatus = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["resultStatus"]
                            if (resultStatus != 2):
                                continue
                            if (len(plotData[tdv]) == 0):
                                plotData[tdv] = {"iters" : [], "timestamps" : [], "phaseDiffs" : []}
                            for i in range(len(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["iters"])):
                                if (i >= len(plotData[tdv]["iters"])):
                                    plotData[tdv]["iters"].append(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["iters"][i])
                                    plotData[tdv]["timestamps"].append([])
                                    plotData[tdv]["phaseDiffs"].append([])
                                plotData[tdv]["timestamps"][i].append(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["timestamps"][i])
                                plotData[tdv]["phaseDiffs"][i].append(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["phases"][i] - data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"])
                fig, axes = plt.subplots(nrows = 1, ncols = 1, figsize = (8, 6), dpi = 300)
                for tdv in plotData:
                    axPlot = axes
                    if (len(plotData[tdv]) > 0):
                        timeData = []
                        phaseDiffMeanData = []
                        phaseDiffDevData = []
                        for i in range(len(plotData[tdv]["iters"])):
                            timeData.append(np.mean(plotData[tdv]["timestamps"][i]))
                            phaseDiffMeanData.append(np.mean(plotData[tdv]["phaseDiffs"][i]))
                            phaseDiffDevData.append(np.std(plotData[tdv]["phaseDiffs"][i]))
                        timeData = np.array(timeData) / 1000000
                        phaseDiffMeanData = (np.array(phaseDiffMeanData) / targetDuty) * 100
                        phaseDiffDevData = (np.array(phaseDiffDevData) / targetDuty) * 100
                        axPlot.plot(timeData, phaseDiffMeanData, c = TDVPlotColors[tdv][0], linewidth = 2, label = "Result TDV")
                        axPlot.fill_between(timeData, phaseDiffMeanData - phaseDiffDevData, phaseDiffMeanData + phaseDiffDevData, color = TDVPlotColors[tdv][1], alpha = 0.2)
                        finalPhaseIdx = 0
                        for i in range(len(timeData)):
                            if (timeData[i] >= timeLimit):
                                finalPhaseIdx = i
                                break
                        finalPhase = phaseDiffMeanData[finalPhaseIdx]
                        if (finalPhase <= 40) and (finalPhase >= -40):
                            finalPhaseStr = str(round(finalPhase)) + "%"
                            for i in range(max(0, 4 - len(finalPhaseStr))):
                                finalPhaseStr += "  "
                            axPlot.annotate(finalPhaseStr, 
                                            xy = (timeLimit, finalPhase),
                                            xytext = (timeLimit + (timeLimit * 0.02), finalPhase),
                                            xycoords = "data",
                                            textcoords = "data",
                                            ha = "left", 
                                            va = "center",
                                            arrowprops = dict(color = TDVPlotColors[tdv][0], arrowstyle = "->"),
                                            annotation_clip = False,
                                            color = TDVPlotColors[tdv][0])
                    axPlot.axhline(y = 0, color = TDVPlotColors[tdv][1], linewidth = 2, alpha = 0.5, linestyle = "dashed")
                    axPlot.axhline(y = tolerance * 100, color = "red", linestyle = "dashed", linewidth = 0.5)
                    axPlot.axhline(y = -tolerance * 100, color = "red", linestyle = "dashed", linewidth = 0.5)
                    axPlot.set_xlim([0, timeLimit])
                    axPlot.set_ylim(-100, 100)
                    axPlot.xaxis.set_major_locator(MultipleLocator(timeLimit / 10))
                    axPlot.yaxis.set_major_locator(MultipleLocator(20))
                    axPlot.grid(which = "both")
                    if (testType != 0):
                        axPlot.set_title(GetTDVOperationName(testType, tdv), fontsize = "small")
                if (testType == 0):
                    fig.suptitle("TDV ΔΦ Error vs. Time (" + operation + ")")
                else:
                    fig.suptitle("TDV ΔΦ Error vs. Time (" + operation + ", $t_{ocd}$: " + str(tocd) + " μs)")
                fig.supxlabel("Time (s)")
                fig.supylabel("ΔΦ Error (%)")
                handles, labels = axes.get_legend_handles_labels()
                fig.legend(handles, labels, ncols = 1, loc = "lower left", fontsize = "small")
                plt.tight_layout()
                if (show is True):
                    plt.show()
                if (len(savePath) > 0):
                    fullSavePath = savePath + "operating_cycles_" + str(targetDuty) + "\\" + operation + "\\tocd_" + str(tocd) + "\\"
                    os.makedirs(fullSavePath, exist_ok = True)
                    plt.savefig(fullSavePath + "error_v_time.png")
                plt.clf()
                plt.close()

def PlotErrorVsTimePerOperationAll(data: dict, tolerance: float, timeLimit: float, show: bool, savePath: str) -> None:
    for targetDuty in data:
        for testType in data[targetDuty]:
            operation = OperationTypes[testType]
            for tocd in data[targetDuty][testType]:
                print("plotting TDV error vs. time for " + operation + " (" + str(targetDuty) + ", " + str(tocd) + ")...")
                plotNum = 3
                if (testType == 1) or (testType == 2):
                    plotNum = 2
                plotData = {0 : {}, 1 : {}, 2 : {}}
                for testIdx in data[targetDuty][testType][tocd]:
                    for runIdx in data[targetDuty][testType][tocd][testIdx]:
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            if (len(plotData[tdv]) == 0):
                                plotData[tdv] = {"iters" : [], "timestamps" : [], "phaseDiffs" : []}
                            for i in range(len(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["iters"])):
                                if (i >= len(plotData[tdv]["iters"])):
                                    plotData[tdv]["iters"].append(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["iters"][i])
                                    plotData[tdv]["timestamps"].append([])
                                    plotData[tdv]["phaseDiffs"].append([])
                                plotData[tdv]["timestamps"][i].append(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["timestamps"][i])
                                plotData[tdv]["phaseDiffs"][i].append(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["phases"][i] - data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"])
                fig, axes = plt.subplots(nrows = plotNum, ncols = 1, figsize = (8, 6), dpi = 300)
                for tdv in plotData:
                    if (tdv >= plotNum):
                        continue
                    axPlot = axes[tdv]
                    if (len(plotData[tdv]) > 0):
                        timeData = []
                        phaseDiffMeanData = []
                        phaseDiffDevData = []
                        for i in range(len(plotData[tdv]["iters"])):
                            timeData.append(np.mean(plotData[tdv]["timestamps"][i]))
                            phaseDiffMeanData.append(np.mean(plotData[tdv]["phaseDiffs"][i]))
                            phaseDiffDevData.append(np.std(plotData[tdv]["phaseDiffs"][i]))
                        timeData = np.array(timeData) / 1000000
                        phaseDiffMeanData = (np.array(phaseDiffMeanData) / targetDuty) * 100
                        phaseDiffDevData = (np.array(phaseDiffDevData) / targetDuty) * 100
                        axPlot.plot(timeData, phaseDiffMeanData, c = TDVPlotColors[tdv][0], linewidth = 2, label = "TDV #" + str(tdv + 1))
                        axPlot.fill_between(timeData, phaseDiffMeanData - phaseDiffDevData, phaseDiffMeanData + phaseDiffDevData, color = TDVPlotColors[tdv][1], alpha = 0.2)
                        finalPhaseIdx = 0
                        for i in range(len(timeData)):
                            if (timeData[i] >= timeLimit):
                                finalPhaseIdx = i
                                break
                        finalPhase = phaseDiffMeanData[finalPhaseIdx]
                        if (finalPhase <= 40) and (finalPhase >= -40):
                            finalPhaseStr = str(round(finalPhase)) + "%"
                            for i in range(max(0, 4 - len(finalPhaseStr))):
                                finalPhaseStr += "  "
                            axPlot.annotate(finalPhaseStr, 
                                            xy = (timeLimit, finalPhase),
                                            xytext = (timeLimit + (timeLimit * 0.02), finalPhase),
                                            xycoords = "data",
                                            textcoords = "data",
                                            ha = "left", 
                                            va = "center",
                                            arrowprops = dict(color = TDVPlotColors[tdv][0], arrowstyle = "->"),
                                            annotation_clip = False,
                                            color = TDVPlotColors[tdv][0])
                    axPlot.axhline(y = 0, color = TDVPlotColors[tdv][1], linewidth = 2, alpha = 0.5, linestyle = "dashed")
                    axPlot.axhline(y = tolerance * 100, color = "red", linestyle = "dashed", linewidth = 0.5)
                    axPlot.axhline(y = -tolerance * 100, color = "red", linestyle = "dashed", linewidth = 0.5)
                    axPlot.set_xlim([0, timeLimit])
                    axPlot.set_ylim(-40, 40)
                    axPlot.xaxis.set_major_locator(MultipleLocator(timeLimit / 10))
                    axPlot.yaxis.set_major_locator(MultipleLocator(20))
                    axPlot.grid(which = "both")
                    if (testType != 0):
                        axPlot.set_title(GetTDVOperationName(testType, tdv), fontsize = "small")
                if (testType == 0):
                    fig.suptitle("TDV ΔΦ Error vs. Time (" + operation + ")")
                else:
                    fig.suptitle("TDV ΔΦ Error vs. Time (" + operation + ", $t_{ocd}$: " + str(tocd) + " μs)")
                fig.supxlabel("Time (s)")
                fig.supylabel("ΔΦ Error (%)")
                handles, labels = [], []
                for ax in axes.flatten():
                    h, l = ax.get_legend_handles_labels()
                    handles += h
                    labels += l
                fig.legend(handles, labels, ncols = 3, loc = "lower left", fontsize = "small")
                plt.tight_layout()
                if (show is True):
                    plt.show()
                if (len(savePath) > 0):
                    fullSavePath = savePath + "operating_cycles_" + str(targetDuty) + "\\" + operation + "\\tocd_" + str(tocd) + "\\"
                    os.makedirs(fullSavePath, exist_ok = True)
                    plt.savefig(fullSavePath + "error_v_time.png")
                plt.clf()
                plt.close() #@\label{line:phaseEvaluation_PlotErrorVsTimePerOperationAll_End}@

def PlotErrorVsTocdPerOperation(data: dict, plotOperandA: bool, plotOperandB: bool, plotResult: bool, tolerance: float, maxIterLimit: int, show: bool, savePath: str) -> None: #@\label{line:phaseEvaluation_PlotErrorVsTocdPerOperation_Start}@
    for targetDuty in data:
        for testType in data[targetDuty]:
            if (testType == 0):
                continue
            operation = OperationTypes[testType]
            print("plotting TDV error vs. tocd for " + operation + " (" + str(targetDuty) + ")...")
            plotData = {0 : {}, 1 : {}, 2 : {}}
            for tocd in data[targetDuty][testType]:
                for testIdx in data[targetDuty][testType][tocd]:
                    for runIdx in data[targetDuty][testType][tocd][testIdx]:
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            resultStatus = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["resultStatus"]
                            if (resultStatus not in plotData):
                                print("WARNING: Unrecognized TDV result status value of " + str(resultStatus) + " encountered!")
                                continue
                            if (tocd not in plotData[resultStatus]):
                                plotData[resultStatus][tocd] = []
                            phaseDiffs = np.array(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["phases"]) - data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"]
                            for i in range(min([maxIterLimit, len(phaseDiffs)])):
                                plotData[resultStatus][tocd].append(phaseDiffs[i])
            tocdLimits = [9999999, -9999999]
            plt.figure(dpi = 300)
            for tdv in plotData:
                tocdData = []
                phaseDiffMeanData = []
                phaseDiffDevData = []
                correctTocds = []
                for tocd in plotData[tdv]:
                    if (len(plotData[tdv][tocd]) > 0):
                        if (((plotOperandA is True) and (tdv == 0)) or ((plotOperandB is True) and (tdv == 1)) or ((plotResult is True) and (tdv == 2))):
                            tocdData.append(tocd)
                            phaseDiffMeanData.append(np.mean(plotData[tdv][tocd]))
                            phaseDiffDevData.append(np.std(plotData[tdv][tocd]))
                            if (GetPhaseDiffCorrectNum(plotData[tdv][tocd], targetDuty, tolerance) >= (len(plotData[tdv][tocd]))):
                                if (tocd not in correctTocds):
                                    correctTocds.append(tocd)
                if (len(tocdData) > 0):
                    phaseDiffMeanData = (np.array(phaseDiffMeanData) / targetDuty) * 100
                    phaseDiffDevData = (np.array(phaseDiffDevData) / targetDuty) * 100
                    plt.plot(tocdData, phaseDiffMeanData, c = TDVPlotColors[tdv][0], linewidth = 2, label = GetTDVOperationName(testType, tdv))
                    plt.fill_between(tocdData, phaseDiffMeanData - phaseDiffDevData, phaseDiffMeanData + phaseDiffDevData, color = TDVPlotColors[tdv][0], alpha = 0.2)
                    tocdLimits[0] = min([tocdLimits[0], min(tocdData)])
                    tocdLimits[1] = max([tocdLimits[1], max(tocdData)])
                if (tdv == 2):
                    for tocd in correctTocds:
                        plt.axvline(x = tocd, color = TDVPlotColors[1][0], alpha = 0.5, linestyle = "dashed", linewidth = 0.3)
            plt.axhline(y = 0, color = "black", linewidth = 2, alpha = 0.5, linestyle = "dashed")
            plt.title("TDV ΔΦ Error vs. $t_{ocd}$ (" + operation + ")")
            plt.xlim(tocdLimits)
            plt.ylim(-100, 100)
            plt.grid(which = "both")
            plt.xlabel("$t_{ocd}$ (μs)")
            plt.ylabel("ΔΦ Error (%)")
            if (show is True):
                plt.show()
            if (len(savePath) > 0):
                fullSavePath = savePath + "operating_cycles_" + str(targetDuty) + "\\" + operation + "\\"
                os.makedirs(fullSavePath, exist_ok = True)
                plt.savefig(fullSavePath + "error_v_tocd.png")
            plt.clf()
            plt.close() #@\label{line:phaseEvaluation_PlotErrorVsTocdPerOperation_End}@

def PlotResultErrorVsOperandValuesPerOperation(data: dict, maxIterLimit: int, show: bool, savePath: str) -> None: #@\label{line:phaseEvaluation_PlotResultErrorVsOperandValuesPerOperation_Start}@
    for targetDuty in data:
        for testType in data[targetDuty]:
            if (testType == 0):
                continue
            operation = OperationTypes[testType]
            for tocd in data[targetDuty][testType]:
                print("plotting TDV result error vs. operands for " + operation + " (" + str(targetDuty) + ", " + str(tocd) + ")...")
                plotData = {}
                for testIdx in data[targetDuty][testType][tocd]:
                    for runIdx in data[targetDuty][testType][tocd][testIdx]:
                        currOperands = [-1, -1]
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            resultStatus = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["resultStatus"]
                            if (resultStatus == 0):
                                currOperands[0] = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"]
                            elif (resultStatus == 1):
                                currOperands[1] = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"]
                            if ((currOperands[0] == -1) and (currOperands[1] == -1)):
                                print("WARNING: Encountered erroneous operands!")
                                continue
                        currOperandIdx = (currOperands[0], currOperands[1])
                        for tdv in data[targetDuty][testType][tocd][testIdx][runIdx]:
                            resultStatus = data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["resultStatus"]
                            if (resultStatus == 2):
                                if (currOperandIdx not in plotData):
                                    plotData[currOperandIdx] = []
                                phaseDiffs = np.array(data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["phases"]) - data[targetDuty][testType][tocd][testIdx][runIdx][tdv]["targetPhase"]
                                for i in range(min([maxIterLimit, len(phaseDiffs)])):
                                    plotData[currOperandIdx].append(phaseDiffs[i])
                operandAData = []
                operandBData = []
                resultDiffMeanData = []
                resultDiffDevData = []
                for operands in plotData:
                    if (len(plotData[operands]) > 0):
                        operandAData.append(operands[0])
                        operandBData.append(operands[1])
                        resultDiffMeanData.append(np.mean(plotData[operands]))
                        resultDiffDevData.append(np.std(plotData[operands]))
                operandAData = (np.array(operandAData) / targetDuty) * 180
                operandBData = (np.array(operandBData) / targetDuty) * 180
                resultDiffMeanData = (np.array(resultDiffMeanData) / targetDuty) * 100
                resultDiffDevData = (np.array(resultDiffDevData) / targetDuty) * 100
                fig = plt.figure(figsize = (8, 6), dpi = 300)
                if ((testType == 1) or (testType == 2)):
                    ax = fig.add_subplot()
                    img = ax.scatter(operandAData, resultDiffMeanData, c = resultDiffDevData, vmin = 0, vmax = 20, cmap = "viridis")
                    ax.axhline(y = 0, linewidth = 2.0, color = "black", linestyle = "dashed", alpha = 0.5)
                    ax.set_xlim(0, 180)
                    ax.set_ylim(-100, 100)
                    ax.grid()
                    ax.set_xlabel("Operand ΔΦ (°)")
                    ax.set_ylabel("Result ΔΦ Error (%)")
                    ax.set_position([ax.get_position().x0, ax.get_position().y0, ax.get_position().width * 0.9, ax.get_position().height])
                    cax = fig.add_axes([0.87, 0.2, 0.02, 0.6])
                    fig.colorbar(img, orientation = "vertical", cax = cax, label = "Result Error Deviation")
                    fig.suptitle("TDV Operation Result ΔΦ Error vs. Operand ΔΦ (" + operation + ", $t_{ocd}$: " + str(tocd) + " μs)")
                else:
                    ax = fig.add_subplot(111, projection = "3d")
                    img = ax.scatter(operandAData, operandBData, resultDiffMeanData, c = resultDiffDevData, vmin = 0, vmax = 20, cmap = "viridis")
                    ax.plot([0, 180], [180, 180], [0, 0], linewidth = 2.0, color = "black", linestyle = "dashed", alpha = 0.5)
                    ax.plot([0, 0], [0, 180], [0, 0], linewidth = 2.0, color = "black", linestyle = "dashed", alpha = 0.5)
                    ax.set_xlim([0, 180])
                    ax.set_ylim([0, 180])
                    ax.set_zlim([-100, 100])
                    ax.set_xlabel("Operand A ΔΦ (°)")
                    ax.set_ylabel("Operand B ΔΦ (°)")
                    ax.set_zlabel("Result ΔΦ Error (%)")
                    ax.set_position([ax.get_position().x0 + 0.03, ax.get_position().y0, ax.get_position().width, ax.get_position().height])
                    cax = fig.add_axes([0.03, 0.2, 0.03, 0.6])
                    fig.colorbar(img, orientation = "vertical", cax = cax, label = "Result Error Deviation")
                    fig.suptitle("TDV Operation Result ΔΦ Error vs. Operand ΔΦ (" + operation + ", $t_{ocd}$: " + str(tocd) + " μs)")
                if (show is True):
                    plt.show()
                if (len(savePath) > 0):
                    fullSavePath = savePath + "operating_cycles_" + str(targetDuty) + "\\" + operation + "\\tocd_" + str(tocd) + "\\"
                    os.makedirs(fullSavePath, exist_ok = True)
                    plt.savefig(fullSavePath + "result_vs_operands.png")
                plt.clf()
                plt.close() #@\label{line:phaseEvaluation_PlotResultErrorVsOperandValuesPerOperation_End}@

def main():
    print("---- SCRIPT STARTED ----\n")

    files = GetFilesInDir(FilesPath)
    data = {}
    for filePath in files:
        if (filePath.endswith(".txt") or filePath.endswith(".TXT")):
            ReadDataFromFile(data, filePath)
    PlotValuesVsTimePerTestRunAll(data, 1, False, "plots\\values_v_time\\")
    PlotErrorVsTimePerOperationAll(data, 0.1, 1, False, "plots\\error_v_time\\")
    #PlotErrorVsTocdPerOperation(data, False, False, True, 0.1, 1, False, "plots\\error_v_tocd\\")
    PlotResultErrorVsOperandValuesPerOperation(data, 2, False, "plots\\result_v_operands\\")

    print("\n\n---- SCRIPT FINISHED ----")

if (__name__ == "__main__"):
    main()