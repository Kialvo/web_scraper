from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.urls import reverse
from .forms import UploadFileForm
from .models import UploadedFile
from .utils import run_process, generate_results_csv
import os

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                uploaded_file = form.save()
                file_path = uploaded_file.file.path
                print(f"File uploaded successfully: {file_path}")
                results = run_process(file_path, max_attempts=2)
                csv_file = generate_results_csv(results)
                return HttpResponseRedirect(f"{reverse('success')}?file={csv_file}")
            except Exception as e:
                print(f"Error processing file: {e}")
                return HttpResponse("Error processing file", status=500)
    else:
        form = UploadFileForm()
    return render(request, 'webscraper/upload.html', {'form': form})

def success(request):
    csv_file = request.GET.get('file')
    print(f"Displaying success page for file: {csv_file}")
    return render(request, 'webscraper/success.html', {'csv_file': csv_file})

def download_file(request):
    file_path = request.GET.get('file')
    if os.path.exists(file_path):
        try:
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            print(f"Serving file for download: {file_path}")
            return response
        except Exception as e:
            print(f"Error serving file: {e}")
            return HttpResponse("Error serving file", status=500)
    else:
        print(f"File not found: {file_path}")
        return HttpResponse("File not found", status=404)
