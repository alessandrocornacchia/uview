## Values

configure values.yaml file to set resource allocation and/or custom
image tags if you modify images

## Deploy

```
cd ./helm
```

Generate manifest

```
helm template online-boutique . -f values.yaml --output-dir ../release
```

Apply: 

```
k apply -f ../release/online-boutique-demo/templates/kubernetes-manifests/
```



