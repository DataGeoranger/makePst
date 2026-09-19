@echo off
set "py=%~dp0makePst.py"
if not exist "%py%" set "py=c:\Cloud\Dropbox\PythonScripts\a0_util\makePst.py"
if not exist "%py%" set "py=p:\MichaelOu\createPst\create_pst.py"
echo %py%

:: check if python is available
where /q python
IF ERRORLEVEL 1 (
    ECHO The application is missing. Ensure it is installed and placed in your PATH.
	if exist "p:\MichaelOu\Miniconda3" set "conda=p:\MichaelOu\Miniconda3"	
	if exist "c:\Miniconda3"           set "conda=c:\Miniconda3"
	echo."%PATH%" | findstr /C:"%conda%"  >nul && (
		echo Found Python in %conda%
		python --version
	) || (
		echo Set up Python Env
		set "PATH=%conda%;%conda%\Library\mingw-w64\bin;%conda%\Library\usr\bin;%conda%\Library\bin;%conda%\Scripts;%conda%\bin;%PATH%"
		python --version
	)
) ELSE (
    ECHO Found Python. Let's go!
)


set xls=Calib202607.xlsm
set pst=tr13

copy /y %xls% %pst%.xlsm

echo creating "%pst%.pst" in "%%~nxI"
python "%py%" "%pst%".pst regul ^
	--set_ctl_xls   "%pst%.xlsm,CONTROL" ^
	--add_pargp_xls "%pst%.xlsm,PARGP" ^
	--add_par_xls   "%pst%.xlsm,PAR_HK"       ^
	--add_par_xls   "%pst%.xlsm,PAR_VK"       ^
	--add_par_xls   "%pst%.xlsm,PAR_SS"       ^
	--add_par_xls   "%pst%.xlsm,PAR_SY"       ^
	--add_par_xls   "%pst%.xlsm,PAR_SFR"      ^
	--add_par_xls   "%pst%.xlsm,PAR_Other"    ^
	--add_par_xls   "%pst%.xlsm,PAR_GHBdh"    ^
	--add_par_xls   "%pst%.xlsm,PAR_RCH"      ^
	--add_obs_xls   "%pst%.xlsm,OBS_HSS"      ^
	--add_obs_xls   "%pst%.xlsm,OBS_HEAD"     ^
	--add_obs_xls   "%pst%.xlsm,OBS_DHDT"     ^
	--add_obs_xls   "%pst%.xlsm,OBS_QSS"      ^
	--add_obs_xls   "%pst%.xlsm,OBS_FLOW"     ^
	--add_obs_xls   "%pst%.xlsm,OBS_LEAK"     ^
	--add_obs_xls   "%pst%.xlsm,OBS_LAKE"     ^
	--add_io_xls    "%pst%.xlsm,IO"           ^
	--add_pp_xls    "%pst%.xlsm,PPcntl"       ^
	--add_pp_xls    "%pst%.xlsm,PPglm"        ^
	--add_comment   "tr01 based ss02iter04"   ^
	--add_comment   "tr02 based ss02iter04; fix the line offset extracting head targets; change the recharge model to mou_fit_lag3_with_new_stations_inalConstrainSlope_LinearHighSlope" ^
	--add_comment   "tr03 based tr02iter03; bring back the recharge scalers to 1" ^
	--add_comment   "tr04 based tr03iter03; add northeast GHB heads as calibration parameters" ^
	--add_comment   "tr05 based tr04g2; add all GHB heads as calibration parameters" ^
	--add_comment   "tr06 based tr05iter02; update the head weights" ^
	--add_comment   "tr07 based tr06iter03 with rch scaler == 1" ^
	--add_comment   "tr12 based tr11iter03 with correct SFR hk parameter" 

pause

