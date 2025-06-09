
#Calculate recharge

#Plain Language
#Get the sum of rainfall for the period
#test simple vs. complex recharge calculations
#Simple= season max-season min *specific yeild
#Complex= if there is a negative change write difference in recharge column, 
#if it is a postive change write in hyperheic exchange column
##then cumsum the negative change for the increase in well water level over the season


###Calculate plot with water rise and strorm rainfall quantity using dangermond sites

gwallhr<-read.csv("data/hourly_well_data.csv")
gwallhr$Date.and.Time<-as.POSIXct(gwallhr$Date.and.Time,format="%Y-%m-%d %H:%M:%S")
