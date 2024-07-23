## Restart the app
get the process id running in port 8501
```
sudo lsof -i :8501
```
kill the process
```
sudo kill -9 <id>
```
run Streamlit again
```
sudo streamlit run main.py --server.port 8501
```