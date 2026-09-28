package tax

func Rate(region string) float64 {
	rates := map[string]float64{"uk": 0.2}
	return rates[region]
}

func Lookup(table []float64, i int) float64 { return table[i] }
